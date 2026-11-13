"""Deterministic constraints shared by local parsing and model validation.

Keep explicit user limits authoritative when a model supplies an interpretation.
Unknown locations are carried to a clarification instead of becoming a default.
"""
import re
import unicodedata
from decimal import Decimal
from .areas import AREAS

DIETARY_LABELS = ('vegetarian', 'jain', 'halal', 'vegan', 'gluten-free')
CURRENCY = r'(?:rupees?|rupaye|rupay|rupaiye|rupaiya|rs\.?|inr)'
AMOUNT = r'(\d[\d,]*(?:\.\d+)?)\s*(k\b)?'
NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11,
    'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
    'seventy': 70, 'eighty': 80, 'ninety': 90,
    'ek': 1, 'do': 2, 'teen': 3, 'tin': 3, 'chaar': 4, 'char': 4,
    'paanch': 5, 'panch': 5,
}


def normalize_amounts(query):
    text = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in query.casefold())
    for original, normalized in {'रुपये': 'rupees', 'रुपए': 'rupees', 'तीन सौ': 'three hundred',
                                 'दो सौ': 'two hundred', 'पांच सौ': 'five hundred'}.items():
        text = text.replace(original, normalized)
    words = '|'.join((*NUMBER_WORDS, 'hundred', 'thousand', 'sau', 'hazaar', 'hazar', 'and'))
    def amount(match):
        total = current = 0
        for word in re.findall(r'[a-z]+', match[0]):
            if word in NUMBER_WORDS: current += NUMBER_WORDS[word]
            elif word in ('hundred', 'sau'): current = max(1, current) * 100
            elif word in ('thousand', 'hazaar', 'hazar'): total += max(1, current) * 1000; current = 0
        return str(total + current)
    # Number words are converted only next to a price marker, not arbitrary prose.
    phrase = r'(?<!\w)(?:' + words + r')(?:[ -]+(?:' + words + r'))*(?!\w)'
    text = re.sub(phrase + r'(?=\s*' + CURRENCY + r'\b)', amount, text)
    text = re.sub(r'(?<=(?:under)\s)' + phrase, amount, text)
    for prefix in ('below ', 'budget ', 'for ', '₹'):
        text = re.sub(re.escape(prefix) + '(' + phrase + r')(?=\s*(?:rupees?\b|[,.!?]|$))',
                      lambda m: prefix + amount(re.match(r'.*', m[1])), text)
    return text


def money_limit(query):
    text = normalize_amounts(query)
    patterns = [r'(?:\b(?:under|below|budget(?: of)?|total|less than|for)\b|₹|\b(?:rs\.?|inr))\s*(?:₹\s*)?' + AMOUNT,
                AMOUNT + r'\s*(?:' + CURRENCY + r'\b|mein\b|me\b|tak\b|ke andar\b)']
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if re.match(r'\s*(?:people|persons|pax|log|logon|km|kilomet)', text[match.end():]): continue
            value = Decimal(match[1].replace(',', '')) * (1000 if match[2] else 1)
            return int(value)
    return None


def requested_location(query):
    text = query.casefold()
    known = next((area for area in sorted(AREAS, key=len, reverse=True)
                  if re.search(r'(?<!\w)' + re.escape(area.casefold()) + r'(?!\w)', text)), None)
    # Explicit mentions outside the Mumbai City/Suburban collection boundary.
    outside = ('Navi Mumbai', 'Mira Road', 'Bhayandar', 'Thane', 'Panvel', 'Vasai',
               'Virar', 'Kalyan', 'Dombivli', 'Airoli', 'Vashi', 'Nerul', 'Belapur',
               'Ulwe', 'Pune', 'Delhi', 'Bengaluru', 'Bangalore')
    unknown = next((area for area in outside if re.search(r'(?<!\w)' + re.escape(area.casefold()) + r'(?!\w)', text)), None)
    if unknown: return None, unknown
    if known: return known, None
    match = re.search(r'\b(?:in|near|around|at)\s+([a-z][a-z .\'-]{1,65}?)(?=\s+(?:under|below|within|for|with|and|please|mein)\b|[,!?;]|$)', text)
    if match:
        place = match[1].strip(' .')
        if place not in ('me', 'my area', 'my location', 'mumbai', 'mumbai city', 'mumbai suburban', 'the area'):
            return None, place.title()
    return None, None


def dietary_requirements(query):
    text = query.casefold()
    labels = []
    for label, pattern in [('vegan', r'\bvegan\b'), ('gluten-free', r'\bgluten[ -]?free\b'),
                           ('jain', r'\bjain\b'), ('halal', r'\bhalal\b'),
                           ('vegetarian', r'(?<![\w-])(?:veg|vegetarian)(?!\w)')]:
        if re.search(pattern, text) and not re.search(r'\b(?:not|no)\s+' + pattern, text): labels.append(label)
    if re.search(r'non[ -]?veg', text): labels = [x for x in labels if x != 'vegetarian']
    return labels


def dietary_values(value):
    """Canonical explicit labels, never infer ingredients from a dish's name."""
    values = list(dict.fromkeys(x.strip().casefold() for x in re.split(r'[,|+]', value or '') if x.strip()))
    if any(x not in DIETARY_LABELS for x in values): raise ValueError('Choose declared dietary labels: ' + ', '.join(DIETARY_LABELS))
    return values


def scope_is_explicit(query):
    return bool(re.search(r'\btotal\b|all[ -]in|including fees|fees (?:included|mila)|kul budget|कुल|per (?:item|dish|person)|each', query, re.I))
