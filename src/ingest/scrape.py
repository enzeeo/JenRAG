import json
import os
import re
import time
import urllib.request
import urllib.parse
import mwparserfromhell

from src.pipeline.config import USER_AGENT, DATA_DIR

API = "https://minecraft.wiki/api.php"
OUT = os.path.join(DATA_DIR, "wiki_pages.json")
BATCH = 50
DELAY = 0.5

# Subpages and categories that aren't useful for RAG
SKIP_SUFFIXES = ("/ED", "/BE", "/BS", "/Asset history", "/Sounds", "/History")
SKIP_CONTAINS = ("(disambiguation)",)


MAXLAG = 5


def fetch_json(params: dict) -> dict:
    params["format"] = "json"
    params["maxlag"] = MAXLAG
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    while True:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        if "error" in data and data["error"].get("code") == "maxlag":
            retry = int(resp.headers.get("Retry-After", DELAY))
            print(f"\n  Server busy (maxlag), retrying in {retry}s...", flush=True)
            time.sleep(retry)
            continue
        return data


def should_skip(title: str) -> bool:
    if any(title.endswith(s) for s in SKIP_SUFFIXES):
        return True
    if any(s in title for s in SKIP_CONTAINS):
        return True
    return False


_DROP_LINE_RE = re.compile(
    r"^("
    r"[a-z]{2,3}:.+"  # interwiki links: es:Creeper, ja:クリーパー
    r"|Category:.+"  # category tags
    r"|File:.+"  # file references
    r"|class=.+"  # sprite/icon markup at line start
    r"|link=.+"  # image link attributes
    r"|alt=.+"  # image alt text
    r"|:\s*"  # lone colon (empty list marker)
    r"|\{\|.*"  # wiki table opening: {| class="wikitable" ...
    r"|\|\}"  # wiki table closing: |}
    r"|\|-"  # wiki table row separator: |-
    r")$"
)
_IMG_STRIP_RE = re.compile(
    r"(thumb\||\d+px\|?"  # thumb|, 128px, 128px|
    r"|\|(right|left|center)"  # |right, |left, |center
    r"|frameless\|?"  # frameless, frameless|
    r"|border\|?"  # border, border|
    r"|upright=[.\d]*\|?"  # upright=0.5, upright=0.5|
    r"|width=\d+x\d+\|?)"  # width=178x178, width=90x90|
)
_IMG_LINE_START_RE = re.compile(r"^(right|left|center)\|")
_INLINE_JUNK_RE = re.compile(
    r"(class=pixel-image\s?"  # inline sprite/icon markup
    r"|style=\"[^\"]*\"\s?)"  # inline style attributes
)


def strip_wikitext(raw: str) -> str:
    text = str(mwparserfromhell.parse(raw).strip_code())
    cleaned: list[str] = []
    for line in text.split("\n"):
        if _DROP_LINE_RE.match(line.strip()):
            continue
        line = _IMG_STRIP_RE.sub("", line)
        line = _IMG_LINE_START_RE.sub("", line)
        line = _INLINE_JUNK_RE.sub("", line)
        s = line.strip()
        if s and s not in ("right", "left", "center"):
            cleaned.append(line)
    return "\n".join(cleaned)


def count_pages() -> int:
    """Count total non-redirect pages in namespace 0 via the API."""
    print("Counting pages...", end="", flush=True)
    total = 0
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "apfilterredir": "nonredirects",
        "aplimit": "max",
    }
    while True:
        data = fetch_json(params)
        total += len(data.get("query", {}).get("allpages", []))
        cont = data.get("continue")
        if not cont:
            break
        params.update(cont)
        time.sleep(DELAY)
    print(f" {total}")
    return total


def fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"


def print_progress(
    fetched: int, total_est: int, kept: int, skipped: int, short: int, t0: float
):
    elapsed = time.time() - t0
    pct = fetched / total_est * 100 if total_est else 0
    rate = fetched / elapsed if elapsed > 0 else 0
    remaining = (total_est - fetched) / rate if rate > 0 else 0

    bar_len = 30
    filled = int(bar_len * fetched / total_est) if total_est else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    line = (
        f"\r  {bar} {pct:5.1f}%  "
        f"{fetched}/{total_est}  "
        f"kept={kept} skip={skipped} short={short}  "
        f"[{fmt_time(elapsed)}<{fmt_time(remaining)}, {rate:.1f} pg/s]"
    )
    print(f"{line:<100}", end="", flush=True)


def scrape_all() -> dict[str, str]:
    total_est = count_pages()

    pages = {}
    params = {
        "action": "query",
        "generator": "allpages",
        "gapnamespace": 0,
        "gapfilterredir": "nonredirects",
        "gaplimit": BATCH,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    }

    kept = 0
    skipped = 0
    short = 0
    fetched = 0
    t0 = time.time()

    while True:
        data = fetch_json(params)
        batch_pages = data.get("query", {}).get("pages", {})

        for _pid, page in batch_pages.items():
            fetched += 1
            title = page["title"]
            if should_skip(title):
                skipped += 1
                continue

            revs = page.get("revisions", [])
            if not revs:
                continue
            raw = revs[0].get("slots", {}).get("main", {}).get("*", "")
            if len(raw) < 300:
                short += 1
                continue

            plaintext = strip_wikitext(raw)
            if len(plaintext.strip()) < 100:
                short += 1
                continue

            pages[title] = plaintext
            kept += 1

        print_progress(fetched, total_est, kept, skipped, short, t0)

        cont = data.get("continue")
        if not cont:
            break
        params.update(cont)
        time.sleep(DELAY)

    print()
    return pages


def main():
    t0 = time.time()
    print(f"Scraping minecraft.wiki (batch={BATCH}, delay={DELAY}s)")
    pages = scrape_all()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(pages, f, ensure_ascii=False)
    elapsed = time.time() - t0
    print(f"Done: {len(pages)} pages -> {OUT} ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
