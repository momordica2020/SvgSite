"""
Download missing FOTW pages from fotw.info.

Usage: python scripts/download_missing_pages.py
"""
import json
import os
import re
import time
from urllib.parse import unquote, quote
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
FLAGS_DIR = BASE_DIR / "flags"
DETAILS_PATH = BASE_DIR / "data" / "flag_details.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (local educational archive project)"

# Primary: fotw.info direct (fast). Fallback: flagspot (redirects to fotw)
URL_TEMPLATES = [
    "https://www.fotw.info/flags/{code}.html",
    "https://flagspot.net/flags/{code}.html",
]


def build_session():
    """Build a requests session that bypasses env proxy settings (they cause hangs)."""
    s = requests.Session()
    s.trust_env = False  # do NOT pick up HTTP_PROXY/HTTPS_PROXY env vars
    s.headers.update({"User-Agent": UA})
    return s


def collect_missing_codes():
    existing_files = set(p.stem for p in FLAGS_DIR.glob("*.html")) if FLAGS_DIR.exists() else set()

    with open(DETAILS_PATH, 'r', encoding='utf-8') as f:
        details = json.load(f)

    all_linked_codes = set()
    for code, det in details.items():
        blocks = det.get("content_blocks") or []
        for b in blocks:
            if b.get("type") == "sub_pages":
                for link in (b.get("links") or []):
                    c = (link.get("code") or "").strip()
                    if c:
                        all_linked_codes.add(c)

    # Filter: drop codes we can't actually download as a standalone HTML page
    valid_codes = set()
    for c in all_linked_codes:
        if '/' in c or '\\' in c:  # path-like, not a single code
            continue
        if '#' in c:  # anchor, not separate page
            continue
        # URL-encoded duplicate check: if URL-decoded matches an existing file, skip
        try:
            c_decoded = unquote(c)
        except Exception:
            c_decoded = c
        if c != c_decoded and c_decoded in existing_files:
            continue
        if not c or len(c) > 60:
            continue
        valid_codes.add(c)

    missing = sorted([
        c for c in valid_codes
        if c not in existing_files and unquote(c) not in existing_files
    ])
    print(f"Linked codes (raw): {len(all_linked_codes)}", flush=True)
    print(f"Linked codes (filtered valid): {len(valid_codes)}", flush=True)
    print(f"Existing flags/*.html files: {len(existing_files)}", flush=True)
    print(f"MISSING (to attempt download): {len(missing)}", flush=True)
    return missing


def is_likely_404(content_bytes, code):
    if len(content_bytes) < 800:
        return True
    text = content_bytes[:5000].decode('utf-8', errors='ignore').lower()
    # Explicit 404 signals
    if '404' in text and ('not found' in text or 'not exist' in text):
        return True
    if '<title>' in text:
        m = re.search(r'<title>([^<]*)</title>', text, re.I)
        if m:
            title = m.group(1).lower().strip()
            if '404' in title or 'not found' in title or 'error page' in title:
                return True
            # Very short title with no mention of country/code/flag is usually a 404 wrapper
            if len(title) < 6 and 'flag' not in title:
                return True
    # FOTW pages usually contain an <hr> and the word "flag" somewhere
    if 'flag' not in text and code not in text:
        return True
    return False


def download_one(session, code):
    """Return (ok: bool, info: str, bytes: int)"""
    last_err = None
    c_quoted = quote(code, safe='')
    for tmpl in URL_TEMPLATES:
        url = tmpl.format(code=c_quoted)
        for attempt in range(2):
            try:
                r = session.get(url, timeout=25, allow_redirects=True, stream=False)
                if r.status_code == 200 and not is_likely_404(r.content, code):
                    dest = FLAGS_DIR / f"{code}.html"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, 'wb') as f:
                        f.write(r.content)
                    return True, r.url, len(r.content)
                if r.status_code == 404:
                    last_err = "HTTP 404"
                    break  # not worth retrying a 404
                if r.status_code == 429:
                    time.sleep(4)
                    last_err = f"HTTP {r.status_code}"
                else:
                    last_err = f"HTTP {r.status_code} ({len(r.content)}B)"
            except requests.exceptions.RequestException as e:
                last_err = f"{type(e).__name__}: {str(e)[:80]}"
                time.sleep(1.0)
        time.sleep(0.25)
    return False, last_err, 0


def main():
    # Clear proxy env vars that cause hangs
    for k in list(os.environ.keys()):
        if k.lower() in ('http_proxy', 'https_proxy', 'all_proxy'):
            del os.environ[k]

    FLAGS_DIR.mkdir(parents=True, exist_ok=True)

    missing = collect_missing_codes()
    if not missing:
        print("No missing pages.", flush=True)
        return

    print("First 15 missing:")
    for c in missing[:15]:
        print("  ", c, flush=True)
    if len(missing) > 30:
        print(f"  ... ({len(missing) - 30} more entries) ...", flush=True)
        for c in missing[-15:]:
            print("  ", c, flush=True)
    print(flush=True)

    session = build_session()

    ok_count = 0
    fail_count = 0
    bytes_total = 0
    failures_list = []
    start = time.time()

    for i, code in enumerate(missing):
        ok, info, nbytes = download_one(session, code)
        if ok:
            ok_count += 1
            bytes_total += nbytes
        else:
            fail_count += 1
            failures_list.append((code, info))
        # Progress report every 25 items or on the last item
        if (i + 1) % 25 == 0 or i == len(missing) - 1:
            elapsed = max(time.time() - start, 0.001)
            rate = (i + 1) / elapsed
            kbps = (bytes_total / 1024.0) / elapsed
            remaining = len(missing) - (i + 1)
            eta_min = (remaining / rate / 60.0) if rate > 0 else 0
            print(
                f"  [{i + 1}/{len(missing)}] OK={ok_count} FAIL={fail_count} "
                f"rate={rate:.1f}/s kbps={kbps:.0f} eta={eta_min:.1f}min",
                flush=True,
            )
        # Small politeness delay between requests
        time.sleep(0.25)

    print(f"\n=== Summary ===", flush=True)
    print(f"Downloaded OK : {ok_count}", flush=True)
    print(f"Failed        : {fail_count}", flush=True)
    print(f"Total data    : {bytes_total/1024:.0f} KB", flush=True)
    print(f"Total time    : {time.time() - start:.1f} s", flush=True)

    if failures_list:
        # Re-check final missing status
        final_exist = set(p.stem for p in FLAGS_DIR.glob('*.html'))
        still_missing = sorted([c for c in missing if c not in final_exist])
        print(f"\nStill missing files (after download attempt): {len(still_missing)}", flush=True)
        # Group failures by error type so it's easier to see what's happening
        error_types = {}
        for c, info in failures_list:
            key = str(info).split(':', 1)[0] if info else 'unknown'
            error_types.setdefault(key, []).append(c)
        print(f"Failures by type: " + {k: len(v) for k, v in error_types.items()}.__repr__(), flush=True)
        # First 60 individual failures
        shown = 0
        for c, info in failures_list:
            if shown >= 60:
                break
            print(f"  {c} : {info}", flush=True)
            shown += 1
        if len(failures_list) > 60:
            print(f"  ... {len(failures_list) - 60} more failures (see error summary above).", flush=True)


if __name__ == "__main__":
    main()
