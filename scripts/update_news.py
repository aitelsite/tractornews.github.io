#!/usr/bin/env python3
"""Fetch public Google News RSS results about Tractor FC and publish a clean JSON feed."""
import json, os, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

QUERIES = [
    'تراکتور تبریز فوتبال', 'باشگاه تراکتور فوتبال',
    'تراکتور نقل و انتقالات فوتبال', 'تراکتور بازی لیگ برتر فوتبال',
    'site:varzesh3.com/news تراکتور', 'site:footballi.net تراکتور فوتبال',
    'site:tasnimnews.ir تراکتور فوتبال', 'site:ana.ir تراکتور فوتبال',
    'site:khabaronline.ir تراکتور فوتبال',
]
TEAM_TERMS = ['تراکتور', 'تراکتورسازی', 'تراکتور تبریز', 'tractor fc', 'زنوزی', 'بیرانوند', 'اسکوچیچ', 'نکونام', 'شجاع خلیل زاده']
FOOTBALL_TERMS = ['فوتبال', 'باشگاه', 'لیگ', 'بازیکن', 'مربی', 'دیدار', 'بازی', 'مسابقه', 'ترکیب', 'گل', 'قهرمان', 'ورزشگاه', 'هوادار', 'قرارداد', 'نقل و انتقال', 'جام', 'داور', 'تمرین', 'تراکتور', 'زنوزی', 'بیرانوند', 'اسکوچیچ']
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TractorNewsBot/1.0; +https://github.com/aitelsite/tractornews.github.io)'}

def clean(s):
    return re.sub(r'\\s+', ' ', (s or '').replace('\\u200c',' ')).strip()

def parse_date(s):
    try:
        d = parsedate_to_datetime(s)
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat()
    except Exception:
        return ''

def fetch(query):
    params = urllib.parse.urlencode({'q': query, 'hl':'fa', 'gl':'IR', 'ceid':'IR:fa'})
    req = urllib.request.Request('https://news.google.com/rss/search?' + params, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as res:
        root = ET.fromstring(res.read())
    rows = []
    for item in root.findall('./channel/item'):
        title = clean(item.findtext('title')); link = clean(item.findtext('link'))
        desc = clean(re.sub('<[^>]+>', ' ', item.findtext('description') or ''))
        source_node = item.find('source'); source = clean(source_node.text if source_node is not None else '')
        pub = parse_date(item.findtext('pubDate') or '')
        hay = (title + ' ' + desc + ' ' + source).lower()
        if not title or not link or not link.startswith('http'): continue
        if not any(term.lower() in hay for term in TEAM_TERMS): continue
        if not any(term.lower() in hay for term in FOOTBALL_TERMS): continue
        rows.append({'title': title, 'link': link, 'published': pub, 'source': source or 'Google News', 'description': desc[:500]})
    return rows

def main():
    items, seen = [], set()
    for q in QUERIES:
        try:
            for row in fetch(q):
                key = row['link'].split('&')[0]
                if key in seen: continue
                seen.add(key); items.append(row)
        except Exception as exc:
            print(f'RSS query failed ({q}): {exc}')
        time.sleep(0.4)
    items.sort(key=lambda x: x.get('published',''), reverse=True)
    os.makedirs('data', exist_ok=True)
    payload = {'updated_at': datetime.now(timezone.utc).isoformat(), 'source': 'Google News RSS', 'count': len(items), 'news': items[:150]}
    with open('data/news.json','w',encoding='utf-8') as f: json.dump(payload,f,ensure_ascii=False,indent=2)
    print(f'Wrote {min(len(items),150)} relevant news items.')
    if not items: print('Warning: no matching items were found; output is valid but empty.')

if __name__ == '__main__': main()
