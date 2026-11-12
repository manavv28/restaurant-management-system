import asyncio
import json
import shutil
import pytest
import httpx
from test_api import client
from app.catalog import structured_menu
from app.menu_documents import publisher_html_menu,fetch_document,document_text,text_price_candidates


def card(name='Fixture noodles',price='₹250'):
    return f'<div class="menu-item"><h4 class="item-title">{name}</h4><span class="item-price">{price}</span></div>'

def section(cards,currency='Pricing is in Indian Rupees (INR).',title='A La Carte'):
    return f'<div class="menu-section"><h2 class="menu-header">{title}</h2>{cards}<p>{currency}</p></div>'

def test_explicit_publisher_prices_exclude_wine_foreign_currency_ranges_and_conflicts():
    good=section(card())
    assert publisher_html_menu(good)[0]['price_paise']==25000
    assert structured_menu(good)[0][0]['method'].startswith('publisher-html')
    assert publisher_html_menu(section(card(),title='Wine'))==[]
    assert publisher_html_menu(section(card(),currency='Prices are in USD'))==[]
    assert publisher_html_menu(section(card(price='250 / 350')))==[]
    assert publisher_html_menu(section(card(price='1,45')))==[]
    assert publisher_html_menu(section(card()+card(price='₹350')))==[]
    assert publisher_html_menu(section(card(price='1,450')))[0]['price_paise']==145000
    assert publisher_html_menu('<p>Fixture noodles near table 250</p>')==[]


def test_conflicting_schema_does_not_fall_back_to_dom_price():
    schemas=''.join('<script type="application/ld+json">'+json.dumps({'@type':'MenuItem','name':'Fixture noodles','offers':{'price':price,'priceCurrency':'INR'}})+'</script>' for price in ('250','350'))
    assert structured_menu(schemas+section(card()))[0]==[]


def test_fetch_respects_robots_and_rejects_redirects_and_google_sources(monkeypatch):
    monkeypatch.setenv('APPROVED_MENU_HOSTS','menu.example.test,maps.google.com')
    with pytest.raises(ValueError,match='Google Maps'):asyncio.run(fetch_document('https://maps.google.com/menu'))
    original=httpx.AsyncClient;seen=[]
    def handler(request):
        seen.append(str(request.url))
        if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow: /menu')
        raise AssertionError('Disallowed menu must not be fetched')
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    with pytest.raises(ValueError,match='robots'):asyncio.run(fetch_document('https://menu.example.test/menu'))
    assert len(seen)==1
    def redirect(request):return httpx.Response(404) if request.url.path=='/robots.txt' else httpx.Response(302,headers={'location':'https://unapproved.example/menu'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(redirect),**kw))
    with pytest.raises(ValueError,match='redirect'):asyncio.run(fetch_document('https://menu.example.test/menu'))


def test_ocr_prices_are_review_only(monkeypatch):
    import app.menu_pilot as pilot
    async def document(url):return {'body':b'fixture','kind':'image','content_hash':'fixture-hash'}
    monkeypatch.setattr(pilot,'fetch_document',document)
    monkeypatch.setattr(pilot,'document_text',lambda doc:('Fixture soup INR 250',True))
    result=asyncio.run(pilot.inspect({'restaurant_id':1,'name':'Fixture','identity_reviewed':True,'menu_url':'https://menu.example.test/menu.png'}))
    assert result['publishable_items']==0 and result['review_candidates'][0]['review_required'] is True
    assert text_price_candidates('Soup INR 250 / 350\nTax INR 5\nSoup 250')==[]


def test_unmatched_restaurant_never_fetches_menu(monkeypatch):
    import app.menu_pilot as pilot
    async def forbidden(url):raise AssertionError('Unmatched branch must not fetch')
    monkeypatch.setattr(pilot,'fetch_document',forbidden)
    result=asyncio.run(pilot.inspect({'name':'Fixture','identity_reviewed':False,'menu_url':'https://other.example/menu'}))
    assert result['publishable_items']==0 and result['status']=='identity_or_source_review_required'


@pytest.mark.skipif(not shutil.which('pdftotext') or not shutil.which('prlimit'),reason='Native PDF tools unavailable')
def test_pdf_text_extraction_is_real_and_never_publishes_candidates():
    stream=b'BT /F1 14 Tf 30 300 Td (Fixture Soup INR 250) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 400] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    pdf=bytearray(b'%PDF-1.4\n');offsets=[0]
    for index,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf.extend(str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    xref=len(pdf);pdf.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n')
    text,ocr=document_text({'kind':'pdf','body':bytes(pdf)})
    assert 'Fixture Soup INR 250' in text and not ocr
    assert text_price_candidates(text)[0]['review_required'] is True


def test_publisher_menu_worker_imports_evidence_and_price_audit(client,monkeypatch):
    import app.catalog_worker as worker
    from sqlalchemy import select
    from app.database import Session,MenuItem,MenuEvidence,CatalogJob
    from test_catalog import source
    with Session() as db:
        item_source=source(db);sid=item_source.id
        db.add(CatalogJob(source_id=sid));db.commit()
    async def page(_):return section(card())
    monkeypatch.setattr(worker,'fetch_menu',page)
    result=asyncio.run(worker.run_one())
    assert result['state']=='succeeded'
    with Session() as db:
        item=db.scalar(select(MenuItem).where(MenuItem.name=='Fixture noodles'))
        evidence=db.get(MenuEvidence,item.id)
        assert item.price_paise==25000 and evidence.active
        assert evidence.method=='publisher-html/INR/dine-in'
        assert evidence.source_id==sid and evidence.expires_at>evidence.fetched_at


def test_worker_recovers_a_failed_database_flush(client,monkeypatch):
    import app.catalog_worker as worker
    from sqlalchemy import select
    from app.database import Session,MenuItem,CatalogJob
    from test_catalog import source
    with Session() as db:
        item_source=source(db);sid=item_source.id
        db.add(CatalogJob(source_id=sid));db.commit()
    async def page(_):return section(card())
    def invalid_insert(db,item_source,*args,**kwargs):
        db.add(MenuItem(restaurant_id=item_source.restaurant_id,name='Invalid fixture',cuisine='Fixture',price_paise=-1))
        db.flush()
    monkeypatch.setattr(worker,'fetch_menu',page)
    monkeypatch.setattr(worker,'persist_menu',invalid_insert)
    result=asyncio.run(worker.run_one())
    assert result['state']=='queued'
    with Session() as db:
        job=db.get(CatalogJob,result['job_id'])
        assert job.attempts==1 and 'IntegrityError' in job.error
        assert not db.scalar(select(MenuItem).where(MenuItem.name=='Invalid fixture'))


def test_many_published_prices_keep_queries_bounded_and_source_label_correct(client):
    from sqlalchemy import event
    from app.database import Session,MenuItem,MenuEvidence,engine
    from app.catalog import persist_menu
    from test_catalog import source
    with Session() as db:
        item_source=source(db);rid=item_source.restaurant_id
        items=[{'name':f'Fixture noodle {i}','price_paise':10000+i,'excerpt':f'Fixture noodle {i} INR 100','method':'publisher-html/INR/dine-in'} for i in range(90)]
        persist_menu(db,item_source,'Explicit isolated fixture',items);db.commit()
    queries=[]
    def record(connection,cursor,statement,*args):
        if statement.lstrip().upper().startswith('SELECT'):queries.append(statement)
    event.listen(engine,'before_cursor_execute',record)
    try:
        response=client.post('/search',json={'query':'Chinese under 500','area':'Bandra','include_samples':False})
        assert response.status_code==200
        matches=[r for r in response.json()['results'] if r['restaurant']['id']==rid]
        assert len(matches)==1 and matches[0]['dish']['price_paise']==10000
        assert 'published menu' in matches[0]['reason'] and 'Owner supplied' not in matches[0]['reason']
        assert len(queries)<=12
        queries.clear()
        details=client.get(f'/restaurants/{rid}')
        assert len(details.json()['menu'])==90
        assert len(queries)<=3
    finally:event.remove(engine,'before_cursor_execute',record)
