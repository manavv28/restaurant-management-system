"""Batch-load public price provenance; a recent retrieval is not a restaurant quote."""
import json
from sqlalchemy import select
from .database import CatalogSource,now
API_METHOD='indiarestros-api/INR'

def source_metadata(db,evidence_by_id):
    ids={e.source_id for e in evidence_by_id.values() if e.method==API_METHOD}
    result={}
    if ids:
        for source in db.scalars(select(CatalogSource).where(CatalogSource.id.in_(ids))):
            try:
                value=json.loads(source.permission_note);result[source.id]=value if isinstance(value,dict) else {}
            except (ValueError,TypeError):result[source.id]={}
    return result

def evidence_metadata(evidence,metadata=None):
    live=evidence.active and evidence.expires_at>now()
    if evidence.method!=API_METHOD:
        return {'price_status':'fresh source observation' if live else 'stale or withdrawn source price','source_expires_at':evidence.expires_at}
    data=(metadata or {}).get(evidence.source_id,{})
    date=data.get('provider_updated_at')
    context=data.get('price_context','listing; dine-in/delivery not specified')
    label='Third-party listing price' if live else 'Stale or withdrawn listing price'
    label+=' · source date '+date[:10] if date else ' · original source date unknown'
    return {'price_status':label+' · '+context+' · confirm current price',
            'source_expires_at':evidence.expires_at,'source_observed_at':date,'source_retrieved_at':evidence.fetched_at,
            'price_context':context,'price_is_reference':True,'original_source':data.get('original_source'),
            'source_url':data.get('provider_menu_url')}
