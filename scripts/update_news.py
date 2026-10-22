#!/usr/bin/env python3
"""Collect Tractor FC football news from broad Persian and international Google News RSS searches."""
import json, os, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Broad searches have no date limit. Recent searches supplement them.
QUERIES = [
    'تراکتور فوتبال', 'باشگاه فوتبال تراکتور تبریز', 'تیم فوتبال تراکتور',
    'تراکتور لیگ برتر ایران', 'تراکتور لیگ نخبگان آسیا',
    'تراکتور نقل و انتقالات', 'تراکتور بازیکنان مربی مصدومیت',
    'تراکتور بازی نتیجه ترکیب گل', 'تراکتور هواداران باشگاه',
    'تراکتور فوتبال when:1d', 'تراکتور فوتبال when:7d',
    'Tractor FC football', 'Tractor Tabriz football club',
    'Tractor Sazi football', 'Tractor FC transfer coach player',
    'Tractor FC AFC Champions League Elite',
    'site:varzesh3.com تراکتور', 'site:footballi.net تراکتور',
    'site:footballiapp.com تراکتور', 'site:tasnimnews.ir تراکتور فوتبال',
    'site:ana.ir تراکتور فوتبال', 'site:khabaronline.ir تراکتور فوتبال',
    'site:isna.ir تراکتور فوتبال', 'site:mehrnews.com تراکتور فوتبال',
    'site:irna.ir تراکتور فوتبال', 'site:fararu.com تراکتور فوتبال',
    'site:footba11.co تراکتور', 'site:persianfootball.com Tractor FC',
    'site:the-afc.com Tractor FC', 'site:bbc.com/persian تراکتور فوتبال',
    'site:iranintl.com تراکتور فوتبال', 'site:reuters.com/sports Tractor FC',
    'site:espn.com/soccer Tractor FC', 'site:apnews.com Tractor FC football',
]
TEAM_TERMS = [
    'تراکتور', 'تراکتورسازی', 'تراکتور تبریز', 'tractor fc', 'tractor sc',
    'tractor sazi', 'traktor', 'زنوزی', 'بیرانوند', 'اسکوچیچ', 'نکونام',
    'ربیعی', 'شجاع خلیل زاده', 'حسین زاده', 'ترابی', 'پوستونسکی',
]
FOOTBALL_TERMS = [
    'فوتبال', 'باشگاه', 'لیگ', 'بازیکن', 'مربی', 'دیدار', 'بازی',
    'مسابقه', 'ترکیب', 'گل', 'قهرمان', 'ورزشگاه', 'هوادار', 'قرارداد',
    'نقل و انتقال', 'جام', 'داور', 'تمرین', 'زنوزی', 'بیرانوند',
    'اسکوچیچ', 'نکونام', 'ربیعی', 'ملوان', 'الشمال', 'صنعت نفت',
    'football', 'soccer', 'afc', 'league', 'coach', 'player', 'match',
    'transfer', 'squad', 'goal', 'tabriz', 'tractor fc', 'tractor sc',
]
AGRICULTURE_TERMS = [
    'تراکتور کشاورزی', 'قطعات تراکتور', 'قیمت تراکتور',
    'ماشین آلات کشاورزی', 'agricultural tractor', 'farm tractor',
    'tractor parts', 'tractor price',
]
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TractorFCNewsBot/1.0)'}

def clean(s):
    return re.sub(r'\\s+', ' ', (s or '').replace('\\u200c', ' ')).strip()

def parse_date(s):
    try:
        d = parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat()
    except Exception:
        return ''

def fetch(query, language, country, edition):
    params = urllib.parse.urlencode({'q': query, 'hl': language, 'gl': country, 'ceid': edition})
    req = urllib.request.Request('https://news.google.com/rss/search?' + params, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as res:
        root = ET.fromstring(res.read())
    rows = []
    for item in root.findall('./channel/item'):
        title = clean(item.findtext('title'))
        link = clean(item.findtext('link'))
        desc = clean(re.sub('<[^>]+>', ' ', item.findtext('description') or ''))
        node = item.find('source')
        source = clean(node.text if node is not None else '')
        pub = parse_date(item.findtext('pubDate') or '')
        hay = (title + ' ' + desc + ' ' + source).lower()
        if not title or not link.startswith('http'):
            continue
        if not any(term.lower() in hay for term in TEAM_TERMS):
            continue
        if any(term in hay for term in AGRICULTURE_TERMS) and not any(term in hay for term in FOOTBALL_TERMS):
            continue
        rows.append({'title': title, 'link': link, 'published': pub,
                     'source': source or 'Google News', 'description': desc[:900]})
    return rows

def main():
    items, seen = [], set()
    editions = [('fa', 'IR', 'IR:fa'), ('en', 'US', 'US:en')]
    for q in QUERIES:
        for language, country, edition in editions:
            try:
                for row in fetch(q, language, country, edition):
                    key = re.sub(r'[?&](oc|ved|usg)=[^&]+', '', row['link']).rstrip('/').lower()
                    if key not in seen:
                        seen.add(key)
                        items.append(row)
            except Exception as exc:
                print(f'RSS query failed ({language}/{q}): {exc}')
            time.sleep(0.15)
    items.sort(key=lambda x: x.get('published', ''), reverse=True)
    os.makedirs('data', exist_ok=True)
    payload = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'Google News RSS; broad Persian and international searches without a fixed date limit',
        'count': len(items),
        'news': items[:500],
    }
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'Wrote {min(len(items), 500)} unique relevant Tractor FC football news items.')
    if not items:
        print('Warning: no items returned; review Google News RSS availability or relevance checks.')

if __name__ == '__main__':
    main()
