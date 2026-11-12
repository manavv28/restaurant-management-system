"""Offline Overture normalization and conservative cross-source identity matching.

No provider calls or menu/price inference. Polygon clipping belongs to the extract step.
"""
import json
import math
import re
import unicodedata
from collections import defaultdict
from urllib.parse import urlsplit
from .areas import AREAS

FOOD_CATEGORIES = {'restaurant','casual_eatery','food_court','cafe','coffee_shop','fast_food_restaurant','food_truck_stand'}
EXCLUDED_TAXONOMIES = {'internet_cafe','candy_store','chocolatier'}

def normalized_name(value):
    return ''.join(c for c in unicodedata.normalize('NFKC',value).casefold() if c.isalnum())

def metres(a,b):
    lat=(a['latitude']+b['latitude'])/2
    return math.hypot((a['latitude']-b['latitude'])*111195,
                      (a['longitude']-b['longitude'])*111195*math.cos(math.radians(lat)))

def normalize(row, release, observed_at):
    """Accept a named, bounded, source-backed food venue; confidence is not a rating."""
    if row.get('basic_category') not in FOOD_CATEGORIES: raise ValueError('not_food')
    primary=(row.get('taxonomy') or {}).get('primary') or ''
    if primary in EXCLUDED_TAXONOMIES: raise ValueError('not_eatery')
    if row.get('operating_status') not in (None,'open'): raise ValueError('closed_or_unknown_status')
    confidence=row.get('confidence')
    if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not .5<=confidence<=1:
        raise ValueError('low_or_missing_confidence')
    name=' '.join(((row.get('names') or {}).get('primary') or '').split())
    if not 2<=len(name)<=150 or not normalized_name(name): raise ValueError('invalid_name')
    external_id=row.get('id','')
    if not re.fullmatch(r'[a-f0-9-]{36}',external_id): raise ValueError('invalid_id')
    b=row['bbox'];lat=(b['ymin']+b['ymax'])/2;lon=(b['xmin']+b['xmax'])/2
    if not (18.85<=lat<=19.35 and 72.75<=lon<=73.05): raise ValueError('outside_mumbai_bbox')
    sources=row.get('sources') or []
    if not sources or any(s.get('license') not in ('CDLA-Permissive-2.0','Apache-2.0','CC0-1.0') for s in sources):
        raise ValueError('unreviewed_licence')
    area=min(AREAS,key=lambda a:(lat-AREAS[a][0])**2+((lon-AREAS[a][1])*math.cos(math.radians(lat)))**2)
    address=next(iter(row.get('addresses') or [{}]))
    address_text=', '.join(str(address[k]) for k in ('freeform','locality','postcode') if address.get(k))
    website=''
    for candidate in row.get('websites') or []:
        try:
            url=urlsplit(candidate)
            if url.scheme=='https' and url.hostname and not url.username and not url.password and url.port in (None,443):
                website=candidate[:2000];break
        except ValueError: pass
    phone=next(iter(row.get('phones') or ['']))[:30]
    cuisine='Unspecified'
    cuisines={'indian':'Indian','chinese':'Chinese','italian':'Italian','japanese':'Japanese','thai':'Thai',
              'korean':'Korean','mexican':'Mexican','lebanese':'Lebanese','seafood':'Seafood','asian':'Asian',
              'south_indian':'South Indian','north_indian':'North Indian','vegetarian':'Vegetarian'}
    for key,value in sorted(cuisines.items(),key=lambda x:-len(x[0])):
        if primary==key+'_restaurant': cuisine=value;break
    licences=', '.join(sorted({s['license'] for s in sources}))
    providers=', '.join(sorted({s['dataset'] for s in sources if s.get('dataset')!='Overture'}))
    return {'name':name,'address':address_text or 'Address unavailable','area':area,'latitude':lat,'longitude':lon,
            'phone':phone,'website':website,'pin_code':address.get('postcode','') if re.fullmatch(r'\d{6}',address.get('postcode') or '') else '',
            'cuisine':cuisine,'source_id':'overture:'+external_id,
            'source':f'Overture Maps {release}; {providers}; {licences}. Source supplied; not independently verified. https://explore.overturemaps.org/?gers_id={external_id}',
            'external_id':external_id,'licence':licences,'observed_at':observed_at,
            'details':json.dumps({'release':release,'category':row['basic_category'],'taxonomy':row.get('taxonomy'),
                                  'confidence':confidence,'operating_status':row.get('operating_status'),'sources':sources},ensure_ascii=False)}

class IdentityMatcher:
    """Stable IDs first, then exact normalized name within 80 m. Branches stay separate."""
    def __init__(self,existing):
        self.by_source={r['source_id']:r for r in existing if r.get('source_id')}
        self.by_name=defaultdict(list)
        for row in existing:self.by_name[normalized_name(row['name'])].append(row)

    def match_or_add(self,row):
        target=self.by_source.get(row['source_id'])
        if target:return target['source_id'],True
        matches=[r for r in self.by_name[normalized_name(row['name'])] if metres(row,r)<=80 and r.get('source_id')]
        if matches:
            target=min(matches,key=lambda r:metres(row,r))
            self.by_source[row['source_id']]=target
            return target['source_id'],True
        self.by_name[normalized_name(row['name'])].append(row)
        self.by_source[row['source_id']]=row
        return row['source_id'],False
