"""Bounded publisher-menu inspection. OCR/PDF observations require review before import."""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from .catalog import approved_url,paise,USER_AGENT

MAX_DOCUMENT_BYTES=5_000_000
MAX_TEXT_BYTES=200_000


def publisher_html_menu(html):
    """Explicit menu-card markup only; never pair arbitrary nearby numbers with dishes."""
    soup=BeautifulSoup(html,'html.parser')
    items=[]
    for section in soup.select('.menu-section'):
        title=section.select_one('.menu-header')
        if not title or title.get_text(' ',strip=True).casefold() not in ('a la carte','à la carte','food menu','dine-in menu'):
            continue
        if not re.search(r'Indian Rupees\s*\(INR\)|prices?\s+(?:are\s+)?in\s+INR',section.get_text(' ',strip=True),re.I):
            continue
        for card in section.select('.menu-item'):
            names=card.select('.item-title');prices=card.select('.item-price')
            if len(names)!=1 or len(prices)!=1:continue
            name=' '.join(names[0].get_text(' ',strip=True).split())
            price=prices[0].get_text(' ',strip=True)
            if not name or len(name)>150:continue
            if not re.fullmatch(r'(?:₹|INR|Rs\.?)?\s*(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?',price,re.I):continue
            value=re.sub(r'^(?:₹|INR|Rs\.?)\s*','',price,flags=re.I).replace(',','').strip()
            try:amount=paise(value)
            except ValueError:continue
            items.append({'name':name,'price_paise':amount,'excerpt':name+' | '+price+' | INR dine-in',
                          'method':'publisher-html/INR/dine-in'})
    grouped={}
    for item in items:grouped.setdefault(item['name'].casefold(),[]).append(item)
    return [rows[0] for rows in grouped.values() if len({row['price_paise'] for row in rows})==1]


async def _bounded(client,url,limit):
    async with client.stream('GET',url) as response:
        if response.is_redirect:raise ValueError('Approve the exact redirect destination separately')
        response.raise_for_status()
        raw=bytearray()
        async for chunk in response.aiter_bytes():
            raw.extend(chunk)
            if len(raw)>limit:raise ValueError('Menu document exceeds byte limit')
        return bytes(raw),response.headers.get('content-type','').split(';')[0].lower()


async def fetch_document(url):
    approved_url(url)
    host=urlsplit(url).hostname
    if any(host==x or host.endswith('.'+x) for x in ('google.com','google.co.in','googleusercontent.com','gstatic.com','googleapis.com','goo.gl')):
        raise ValueError('Google Maps content is not a publisher menu source')
    async with httpx.AsyncClient(timeout=25,follow_redirects=False,headers={'User-Agent':USER_AGENT}) as client:
        try:robots,_=await _bounded(client,'https://'+host+'/robots.txt',100_000)
        except httpx.HTTPStatusError as error:
            if error.response.status_code!=404:raise
            robots=b''
        rules=RobotFileParser();rules.parse(robots.decode('utf-8',errors='replace').splitlines())
        if not rules.can_fetch(USER_AGENT,url):raise ValueError('Source robots.txt disallows collection')
        raw,media=await _bounded(client,url,MAX_DOCUMENT_BYTES)
    if raw.startswith(b'%PDF-'):kind='pdf'
    elif raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff') or (raw.startswith(b'RIFF') and raw[8:12]==b'WEBP'):kind='image'
    elif media in ('text/html','application/xhtml+xml') or raw.lstrip()[:20].lower().startswith((b'<!doctype html',b'<html')):kind='html'
    else:raise ValueError('Unsupported menu document type')
    return {'url':url,'body':raw,'kind':kind,'content_hash':hashlib.sha256(raw).hexdigest()}


def _run(command,timeout):
    limiter=shutil.which('prlimit')
    if not limiter:raise RuntimeError('Document inspection requires prlimit resource bounds')
    subprocess.run([limiter,'--as=268435456','--cpu=20','--fsize=1048576','--',*command],check=True,timeout=timeout,
                   env={**os.environ,'OMP_THREAD_LIMIT':'1','OMP_NUM_THREADS':'1'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def document_text(document):
    """Native tools are time/size bounded; OCR output is always review-only."""
    if document['kind']=='html':
        from .catalog import Page
        page=Page();page.feed(document['body'].decode('utf-8',errors='replace'))
        return '\n'.join(page.text)[:MAX_TEXT_BYTES],False
    with tempfile.TemporaryDirectory(prefix='biteai-menu-') as directory:
        root=Path(directory);source=root/('menu.pdf' if document['kind']=='pdf' else 'menu.img')
        source.write_bytes(document['body']);output=root/'text.txt';ocr=False
        if document['kind']=='pdf':
            if not shutil.which('pdftotext'):raise RuntimeError('PDF extraction requires pdftotext')
            _run(['pdftotext','-f','1','-l','10','-layout','-enc','UTF-8',str(source),str(output)],15)
            if output.stat().st_size>MAX_TEXT_BYTES:raise ValueError('Extracted menu text exceeds limit')
        if document['kind']=='image' or not output.read_text().strip():
            ocr=True
            if document['kind']=='pdf':
                if not shutil.which('pdftoppm'):raise RuntimeError('Scanned PDF review requires pdftoppm')
                _run(['pdftoppm','-f','1','-singlefile','-scale-to','1800','-png',str(source),str(root/'page')],15)
                source=root/'page.png'
            if not shutil.which('tesseract'):raise RuntimeError('Image review requires tesseract')
            _run(['tesseract',str(source),str(root/'text'),'--psm','6','-l','eng'],20)
        if output.stat().st_size>MAX_TEXT_BYTES:raise ValueError('Extracted menu text exceeds limit')
        return output.read_text(),ocr


def text_price_candidates(text):
    """Review candidates only. Ranges, multiple prices and missing INR markers are omitted."""
    output=[]
    for line in text.splitlines():
        match=re.fullmatch(r'\s*([A-Za-z][^\n]{2,145}?)\s+(?:₹|INR|Rs\.?)\s*(\d+(?:\.\d{1,2})?)\s*',line,re.I)
        if not match:continue
        name=match[1].strip(' .');value=match[2]
        if re.search(r'\d|[/|₹]|\b(?:INR|Rs\.?|tax|total|service|minimum|person)\b',name,re.I):continue
        try:amount=paise(value)
        except ValueError:continue
        output.append({'name':name,'price_paise':amount,'excerpt':line.strip(),'review_required':True})
    return output[:200]
