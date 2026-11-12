"""Inspect a small restaurant manifest without publishing OCR guesses or Google photo content."""
import argparse
import asyncio
import json
from datetime import datetime,timezone
from pathlib import Path
from .menu_documents import fetch_document,document_text,text_price_candidates
from .catalog import structured_menu

async def inspect(entry):
    row={key:entry.get(key) for key in ('restaurant_id','name','area','menu_url','identity_reviewed','note')}
    row['checked_at']=datetime.now(timezone.utc).isoformat()
    if not entry.get('identity_reviewed') or not entry.get('menu_url'):
        return row|{'status':'identity_or_source_review_required','publishable_items':0}
    try:
        document=await fetch_document(entry['menu_url'])
        text,ocr=await asyncio.to_thread(document_text,document)
        items=structured_menu(document['body'].decode('utf-8',errors='replace'))[0] if document['kind']=='html' else []
        candidates=[] if items else text_price_candidates(text)
        return row|{'status':'explicit_publisher_prices' if items else 'document_review_required',
                    'format':document['kind'],'content_hash':document['content_hash'],'ocr':ocr,
                    'publishable_items':len(items),'items':items,'review_candidates':candidates,
                    'text_characters':len(text),'partial_document':document['kind']=='pdf'}
    except Exception as error:
        # Never include raw proxy/provider errors or arbitrary source responses.
        return row|{'status':'fetch_or_extraction_failed','error':str(error)[:180] if isinstance(error,ValueError) else type(error).__name__,'publishable_items':0}

async def run(entries):
    if not 1<=len(entries)<=10:raise ValueError('Pilot is limited to 1–10 restaurants')
    # One native OCR/PDF process at a time on Render Free.
    rows=[]
    for entry in entries:rows.append(await inspect(entry))
    return {'area':'Bandra','restaurants_checked':len(rows),'with_explicit_prices':sum(bool(row['publishable_items']) for row in rows),
            'publishable_items':sum(row['publishable_items'] for row in rows),'results':rows,
            'notice':'Publisher observations, not guaranteed live restaurant prices. OCR/PDF candidates are never automatically published. Google Maps photos are not harvested.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report=asyncio.run(run(json.loads(Path(args.manifest).read_text())))
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({key:value for key,value in report.items() if key!='results'}))
if __name__=='__main__':main()
