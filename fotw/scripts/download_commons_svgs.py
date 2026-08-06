"""
Download flag and coat of arms SVG metadata from Wikimedia Commons.
Phase 1: fetch metadata (with proper rate limiting)
Phase 2: download SVG files slowly as cache (re-runnable)
"""
import requests
import json
import os
import re
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
COMMONS_DIR = BASE_DIR / "commons"
SVGS_DIR = COMMONS_DIR / "svgs"
DATA_DIR = COMMONS_DIR / "data"

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "FOTW-SVG-Browser/1.0 (local educational project)"
HEADERS = {"User-Agent": USER_AGENT}

SEARCH_QUERIES = [
    "Flag of national svg",
    "Coat of arms svg national",
    "National flag svg country",
    "Civil ensign svg",
    "State ensign svg",
    "Naval ensign svg",
    "War ensign svg",
    "War flag svg",
    "Military flag svg armed forces",
    "Presidential standard svg",
    "Royal standard svg",
    "Government flag svg",
    "State flag svg",
    "Civil flag svg",
    "Air force ensign svg",
    "Ensign of svg",
    "Flag of svg historical",
    "Coat of arms of svg",
    "National coat of arms svg",
]

def api_get(params, retries=3):
    params["format"] = "json"
    params["action"] = "query"
    for attempt in range(retries):
        try:
            r = requests.get(API, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  API error: {e}")
                return None
    return None

def search_files(query, limit=40):
    results = []
    params = {
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": str(limit),
        "srprop": "snippet|size|timestamp",
    }
    cont = True
    while cont and len(results) < limit:
        data = api_get(params)
        if not data: break
        items = data.get("query", {}).get("search", [])
        for item in items:
            title = item.get("title", "")
            if title.startswith("File:") and title.lower().endswith(".svg"):
                results.append(title)
        if "continue" in data and len(results) < limit:
            params.update(data["continue"])
            time.sleep(1)
        else:
            cont = False
    return results

def get_image_info_batch(titles):
    params = {
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiextmetadatafilter": "Artist|LicenseShortName|Credit|DateTime|ObjectName|ImageDescription|Source|LicenseUrl|UsageTerms",
        "iiurlwidth": "600",
    }
    data = api_get(params)
    if not data: return {}
    pages = data.get("query", {}).get("pages", {})
    result = {}
    for pid, page in pages.items():
        title = page.get("title", "")
        iis = page.get("imageinfo", [])
        if not iis: continue
        ii = iis[0]
        meta = ii.get("extmetadata", {})
        def clean(v):
            if not v: return ""
            s = v.get("value", "")
            s = re.sub(r'<[^>]+>', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s
        def rawhtml(v):
            if not v: return ""
            return v.get("value", "")
        info = {
            "title": title,
            "pageid": page.get("pageid", 0),
            "url": ii.get("url", ""),
            "thumburl": ii.get("thumburl", ""),
            "thumbwidth": ii.get("thumbwidth", 0),
            "thumbheight": ii.get("thumbheight", 0),
            "descriptionurl": ii.get("descriptionurl", ""),
            "descriptionshorturl": ii.get("descriptionshorturl", ""),
            "width": ii.get("width", 0),
            "height": ii.get("height", 0),
            "size": ii.get("size", 0),
            "mime": ii.get("mime", ""),
            "object_name": clean(meta.get("ObjectName", {})),
            "description": clean(meta.get("ImageDescription", {})),
            "description_html": rawhtml(meta.get("ImageDescription", {})),
            "artist": clean(meta.get("Artist", {})),
            "artist_html": rawhtml(meta.get("Artist", {})),
            "credit": clean(meta.get("Credit", {})),
            "credit_html": rawhtml(meta.get("Credit", {})),
            "source": clean(meta.get("Source", {})),
            "source_html": rawhtml(meta.get("Source", {})),
            "license": clean(meta.get("LicenseShortName", {})),
            "license_url": clean(meta.get("LicenseUrl", {})),
            "date_time": clean(meta.get("DateTime", {})),
            "usage_terms": clean(meta.get("UsageTerms", {})),
        }
        cats = []
        tl = title.lower()
        if 'coat of arms' in tl or 'coat-of-arms' in tl or 'arms of' in tl or 'royal arms' in tl:
            cats.append('coat_of_arms')
        if 'ensign' in tl: cats.append('ensign')
        if 'naval' in tl or 'navy' in tl: cats.append('naval')
        if 'war flag' in tl or 'war ensign' in tl or 'military' in tl or 'armed forces' in tl or 'army' in tl:
            cats.append('military')
        if 'air force' in tl: cats.append('air_force')
        if 'coast guard' in tl: cats.append('coast_guard')
        if 'presidential' in tl or 'president' in tl: cats.extend(['government','standard'])
        if 'royal standard' in tl or 'royal flag' in tl: cats.extend(['royal','standard'])
        if 'civil' in tl: cats.append('civil')
        if 'state flag' in tl or 'state ensign' in tl: cats.append('government')
        if 'historical' in tl or re.search(r'\(\d{4}', tl): cats.append('historical')
        if not cats: cats.append('national')
        info["categories"] = list(dict.fromkeys(cats))
        result[title] = info
    return result

def safe_filename(title):
    name = title.replace("File:", "")
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    return name

def download_svg(url, dest_path, delay=1.0):
    try:
        time.sleep(delay)
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 429:
            time.sleep(8)
            r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception:
        return False

def build_keywords(item):
    kws = set()
    skip = {'the','and','for','with','from','that','this','svg','flag','file','commons',
            'wikimedia','wikipedia','public','domain','author','source','license','also',
            'known','used','were','which','their','have','been','has','was','are','but'}
    for field in ["object_name", "description", "artist", "credit"]:
        text = item.get(field, "")
        if text:
            words = re.findall(r'[a-zA-Z\u0080-\xff]{3,}', text.lower())
            for w in words[:15]:
                if w not in skip and len(w) >= 3:
                    kws.add(w)
    name = item["title"].replace("File:", "").replace(".svg", "")
    for w in re.findall(r'[a-zA-Z\u0080-\xff]{3,}', name.lower()):
        if w not in {'flag','flags','svg','file','the','and'}:
            kws.add(w)
    item["keywords"] = sorted(kws)[:25]

def main():
    SVGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data_path = DATA_DIR / "commons_svgs.json"
    existing = {"svgs": [], "total": 0}
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing_map = {item["title"]: item for item in existing.get("svgs", [])}
    print(f"Loaded existing: {len(existing_map)} entries")

    print("\n=== Searching Wikimedia Commons ===")
    all_titles = set(existing_map.keys())
    for q in SEARCH_QUERIES:
        print(f"  Query: {q}")
        titles = search_files(q, limit=40)
        new_count = sum(1 for t in titles if t not in all_titles)
        for t in titles:
            all_titles.add(t)
        print(f"    Found {len(titles)}, {new_count} new (total: {len(all_titles)})")
        time.sleep(1.5)

    skip_re = re.compile(r'\bmap\b|\bicon\b|\blogo\b|\bbutton\b|\bbadge\b|\btemplate\b|\bnavbox\b|protest art|symbol flag|insignia', re.I)
    filtered = [t for t in sorted(all_titles) if not skip_re.search(t)]
    print(f"After filtering: {len(filtered)}")

    print("\n=== Fetching metadata ===")
    new_titles = [t for t in filtered if t not in existing_map]
    print(f"Need metadata for {len(new_titles)} new files")

    batch_size = 8
    for i in range(0, len(new_titles), batch_size):
        batch = new_titles[i:i+batch_size]
        info_map = get_image_info_batch(batch)
        for title, info in info_map.items():
            existing_map[title] = info
        print(f"  Batch {i//batch_size+1}/{(len(new_titles)+batch_size-1)//batch_size}: +{len(info_map)} (total: {len(existing_map)})")
        time.sleep(1.5)

    svgs_list = list(existing_map.values())
    for item in svgs_list:
        build_keywords(item)

    print("\n=== Downloading missing SVGs ===")
    downloaded = skipped = failed = 0
    for item in svgs_list:
        lf = item.get("local_file", "")
        if lf and (SVGS_DIR.parent / lf).exists():
            skipped += 1
            continue
        url = item.get("url", "")
        fname = safe_filename(item["title"])
        local_path = SVGS_DIR / fname
        if local_path.exists() and local_path.stat().st_size > 100:
            item["local_file"] = f"svgs/{fname}"
            skipped += 1
            continue
        if url and download_svg(url, local_path, delay=1.5):
            item["local_file"] = f"svgs/{fname}"
            downloaded += 1
        else:
            failed += 1
    print(f"Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")

    for item in svgs_list:
        build_keywords(item)

    output = {
        "total": len(svgs_list),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "Wikimedia Commons",
        "svgs": svgs_list,
    }
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=1)
    print(f"\nDone! {len(svgs_list)} entries saved to {data_path}")

if __name__ == "__main__":
    main()
