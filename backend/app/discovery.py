"""Discover approved menu links without inventing menu contents or fetching restricted hosts."""
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
from .catalog import approved_url

def menu_candidates(html,base):
    candidates=[]
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            if tag!='a':return
            href=dict(attrs).get('href','');url=urljoin(base,href).split('#')[0]
            if not any(word in urlsplit(url).path.lower() for word in ('menu','food','dining')):return
            if urlsplit(url).hostname!=urlsplit(base).hostname:return
            try:approved_url(url)
            except ValueError:return
            if url not in candidates and not url.lower().endswith('.pdf'):candidates.append(url)
    Links().feed(html)
    return candidates[:5]

def classify(name):
    value=name.casefold()
    if any(word in value for word in ('tea','coffee','juice','lassi','drink')):return 'Drinks'
    if any(word in value for word in ('cake','ice cream','dessert','gulab','sweet')):return 'Desserts'
    if any(word in value for word in ('soup','salad','starter','appetizer')):return 'Starters'
    return 'Main'
