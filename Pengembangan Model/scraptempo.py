# tempo_hukum_scraper_nolimit.py
# Scrape Tempo.co kanal Hukum, tanpa batas jumlah artikel/halaman listing.
# Fitur: follow multi-page artikel, content bersih, filter 3 tahun terakhir (opsional).

import re, csv, time, sys, argparse, logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, urljoin
from typing import Optional

import requests
from bs4 import BeautifulSoup

# =======================
# Konfigurasi dasar
# =======================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id,en;q=0.8",
}
REQ_TIMEOUT = 15
DELAY = 0.30
MAX_RETRIES = 3
BACKOFF = 1.25

ALLOWED_HOSTS = {"tempo.co", "www.tempo.co"}

# default kanal = hukum; regex akan dioverride jika --rubric diubah
TEMPO_ART_RE = re.compile(r"^/hukum/[^/?#]+-\d{6,}$", re.I)

STOP_PHRASES = [
    "pilihan editor", "baca juga", "scroll ke bawah", "podcast rekomendasi tempo",
    "berlangganan", "gabung tempo circle"
]

# ======= Tanggal Tempo =======
ID_MON_MAP = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12
}
ID_TZ_OFF = {"WIB": 7, "WITA": 8, "WIT": 9}
ID_MON_FULL = r"(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)"
ID_TZ = r"(?:WIB|WITA|WIT)"
DATE_RE = re.compile(
    rf"(\d{{1,2}})\s+{ID_MON_FULL}\s+(\d{{4}})(?:\s*\|\s*(\d{{1,2}})\.(\d{{2}})\s*({ID_TZ})?)?",
    re.I
)

# =======================
# Utilitas HTTP
# =======================
def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def http_get(session: requests.Session, url: str, timeout=REQ_TIMEOUT) -> requests.Response:
    last_err: Optional[BaseException] = None
    for att in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=timeout, allow_redirects=True)
            if r.status_code == 403:
                ua = session.headers.get("User-Agent", "")
                # safe replace: kalau pattern tidak cocok, tetap aman
                session.headers["User-Agent"] = ua.replace("Chrome/123", "Chrome/120")
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            time.sleep((BACKOFF ** (att - 1)) * 0.6)
    # pastikan kita raise objek Exception yang valid
    if last_err is None:
        raise RuntimeError("http_get gagal tanpa exception spesifik")
    raise last_err

def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    r = http_get(session, url, timeout=REQ_TIMEOUT)
    return BeautifulSoup(r.text, "html.parser")

def build_page_url(base_url: str, page_num: int) -> str:
    if page_num == 1:
        return base_url
    parts = list(urlparse(base_url))
    qs = parse_qs(parts[4])
    qs["page"] = [str(page_num)]
    parts[4] = urlencode(qs, doseq=True)
    return urlunparse(parts)

def strip_fragment(u: str) -> str:
    p = list(urlparse(u)); p[5] = ""
    return urlunparse(p)

def tx(el) -> Optional[str]:
    return el.get_text(" ", strip=True) if el else None

def is_noise_text(s: str) -> bool:
    low = s.lower()
    return any(k in low for k in STOP_PHRASES) or len(low) < 2

# =======================
# Parsing tanggal → ISO UTC
# =======================
def parse_tempo_date_to_aware_iso(s: str) -> Tuple[Optional[str], Optional[datetime]]:
    if not s: return None, None
    m = DATE_RE.search(s)
    if not m: return None, None

    dd = int(m.group(1))
    mon = ID_MON_MAP.get(m.group(2).lower())
    yy = int(m.group(3))
    HH = int(m.group(4)) if m.group(4) else 0
    MM = int(m.group(5)) if m.group(5) else 0
    tzlabel = (m.group(6) or "WIB").upper()
    tz = timezone(timedelta(hours=ID_TZ_OFF.get(tzlabel, 7)))
    try:
        loc = datetime(yy, mon, dd, HH, MM, tzinfo=tz)
        utc = loc.astimezone(timezone.utc)
        return utc.isoformat(), utc
    except Exception:
        return None, None

# =======================
# Cleaners & pickers
# =======================
def clean_node(node):
    if not node: return
    for sel in [
        "script","style","aside","nav","iframe","noscript","form",
        ".ads",".iklan",".share",".baca-juga",".related",".remp-banner",
        ".disco-widget",".podcast",".podcast-rekomendasi",".paywall-cta",
        "#feature_image",".caption",".breadcrumb",".sticky",
    ]:
        for n in node.select(sel):
            n.decompose()

def extract_released_tempo(header_scope, soup):
    if header_scope:
        cand = header_scope.select_one("p")
        if cand:
            s = tx(cand)
            if s and DATE_RE.search(s):
                return s
        for p in header_scope.select("p"):
            s = tx(p)
            if s and DATE_RE.search(s):
                return s
    m = DATE_RE.search(soup.get_text(" ", strip=True))
    return m.group(0) if m else ""

def pick_highlight_tempo(soup, header_scope):
    scope = header_scope or soup
    h1 = scope.select_one("h1")
    if h1:
        sib = h1.find_next_sibling()
        hops = 0
        while sib and hops < 5:
            classes = " ".join(sib.get("class", []))
            if "font-roboserif" in classes or sib.name in ("div","p","h2"):
                t = tx(sib)
                if t and not is_noise_text(t) and len(t) > 20:
                    return t
            sib = sib.find_next_sibling(); hops += 1
    el = scope.select_one(".font-roboserif")
    if el:
        t = tx(el)
        if t and not is_noise_text(t) and len(t) > 20:
            return t
    return ""

def extract_content_wrappers(soup: BeautifulSoup) -> List[str]:
    wrappers = soup.select("#content-wrapper")
    if not wrappers: wrappers = [soup]
    chunks = []
    for w in wrappers:
        clean_node(w)
        for p in w.find_all("p"):
            t = tx(p)
            if not t: continue
            if is_noise_text(t): continue
            if re.match(r"(?i)^\s*(pilihan editor|baca juga)\s*:", t): continue
            chunks.append(t)
    seen, out = set(), []
    for t in chunks:
        s = t.strip()
        if s and s not in seen:
            seen.add(s); out.append(s)
    return out

def extract_tags_tempo(soup: BeautifulSoup) -> List[str]:
    containers = [
        "#article-tags", ".article-tags", ".tags", ".tag-list", ".tag__list",
        ".card-tags", ".meta-tags", ".box-tags", "[class*=tag]"
    ]
    raw = []

    # cari container yang berisi link/tag
    box = None
    for sel in containers:
        box = soup.select_one(sel)
        if box:
            break

    # kalau tidak ketemu satu box spesifik, scan global tapi tetap hati-hati
    search_scope = box if box else soup

    # prefer <a> dulu (paling umum)
    for a in search_scope.select("a[href]"):
        t = (a.get_text(" ", strip=True) or "").strip()
        if t and t.lower() not in ("tag", "tags"):
            raw.append(t)

    # fallback: item <li> tanpa <a>
    if not raw:
        for li in search_scope.select("li"):
            t = (li.get_text(" ", strip=True) or "").strip()
            if t and t.lower() not in ("tag", "tags"):
                raw.append(t)

    # normalisasi + dedup urut
    out, seen = [], set()
    for t in raw:
        k = t.strip()
        if not k:
            continue
        # singkirkan yang terlalu umum
        if k.lower() in ("tag", "tags"):
            continue
        if k not in seen:
            seen.add(k); out.append(k)
    return out

# =======================
# Multipage dalam artikel
# =======================
def find_next_article_page_url(current_url: str, soup: BeautifulSoup) -> Optional[str]:
    a = soup.select_one('a[rel="next"]')
    if a and a.get("href"):
        return urljoin(current_url, a["href"])
    pr = urlparse(current_url)
    base_path = pr.path
    candidates = []
    for link in soup.select("a[href]"):
        href = link.get("href") or ""
        absu = urljoin(current_url, href)
        pr2 = urlparse(absu)
        if pr2.netloc.lower() not in ALLOWED_HOSTS:
            continue
        if pr2.path == base_path:
            qs = parse_qs(pr2.query or "")
            if "page" in qs:
                try:
                    n = int(qs["page"][0])
                    candidates.append((n, absu))
                except:
                    pass
    if candidates:
        candidates.sort()
        for n, u in candidates:
            if n >= 2:
                return u
    return None

def scrape_article_all_pages(session: requests.Session, first_url: str) -> Tuple[str, List[str], str, str, List[str]]:
    visited = set()
    url = first_url
    all_paras: List[str] = []
    title = ""
    released_raw = ""
    highlight = ""
    tags: List[str] = []
    page_idx = 0

    while url and url not in visited:
        visited.add(url)
        soup = get_soup(session, url)
        page_idx += 1

        main = soup.select_one("main") or soup
        header_scope = None
        for cand in [main, soup]:
            hdr = cand.find("h1")
            if hdr:
                header_scope = hdr.parent if hdr.parent else cand
                break

        if page_idx == 1:
            title = tx(soup.select_one("h1")) or title
            released_raw = extract_released_tempo(header_scope, soup) or released_raw
            highlight = pick_highlight_tempo(soup, header_scope) or highlight
            tags = extract_tags_tempo(soup)  # <<–– ambil tag di halaman pertama

        paras = extract_content_wrappers(soup)
        all_paras.extend(paras)

        next_url = find_next_article_page_url(url, soup)
        if not next_url or next_url in visited:
            break
        url = next_url
        time.sleep(DELAY)

    # dedup paragraf
    seen, merged = set(), []
    for p in all_paras:
        if p not in seen:
            seen.add(p); merged.append(p)

    return (title, merged, released_raw, highlight, tags)

# =======================
# Scraper artikel tunggal
# =======================
def guard_domain(url):
    pr = urlparse(url)
    if pr.netloc.lower() not in ALLOWED_HOSTS:
        raise ValueError(f"Host tidak didukung: {pr.netloc}")

def scrape_article_tempo(session: requests.Session, url: str) -> Dict:
    guard_domain(url)
    pr = urlparse(url)
    if not TEMPO_ART_RE.match(pr.path):
        raise ValueError("Bukan URL artikel kanal yang valid.")

    title, paragraphs, released_raw, highlight, tags = scrape_article_all_pages(session, url)
    released_iso, _ = parse_tempo_date_to_aware_iso(released_raw)
    content = "\n\n".join(paragraphs).strip()

    return {
        "source": "tempo",
        "url": url,
        "released_iso": released_iso or "",
        "released_raw": released_raw or "",
        "title": title or "",
        "highlight": highlight or "",
        "content": content,
        "tag": ", ".join(tags) if tags else ""  # <<–– isi tag
    }

# =======================
# Discovery URL tanpa batas
# =======================
def collect_urls_unlimited(session: requests.Session, rubric: str) -> List[str]:
    seeds = [
        f"https://www.tempo.co/{rubric}",
        f"https://www.tempo.co/indeks?category=rubrik&rubric_slug={rubric}",
    ]
    urls, seen = [], set()
    EMPTY_STREAK_LIMIT = 5
    for seed in seeds:
        page = 1
        empty_streak = 0
        while True:
            u = build_page_url(seed, page)
            try:
                soup = get_soup(session, u)
            except Exception as e:
                logging.warning(f"Listing gagal ({u}): {e}")
                empty_streak += 1
                if empty_streak >= EMPTY_STREAK_LIMIT: break
                page += 1; continue

            found_this_page = 0
            for a in soup.select("a[href]"):
                href = a.get("href") or ""
                absu = urljoin(u, href)
                absu = strip_fragment(absu)
                pr2 = urlparse(absu)
                if pr2.netloc.lower() not in ALLOWED_HOSTS:
                    continue
                if not TEMPO_ART_RE.match(pr2.path):
                    continue
                if absu not in seen:
                    seen.add(absu)
                    urls.append(absu)
                    found_this_page += 1

            logging.info(f"[{rubric}] page {page}: +{found_this_page} url")
            if found_this_page == 0:
                empty_streak += 1
            else:
                empty_streak = 0
            if empty_streak >= EMPTY_STREAK_LIMIT:
                break
            page += 1
            time.sleep(DELAY)
    return urls

# =======================
# CSV saver
# =======================
def save_rows_to_csv(rows: List[Dict], csv_path: str):
    fields = ["source","url","released_iso","released_raw","title","highlight","content","tag"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in rows:
            w.writerow({k: d.get(k, "") for k in fields})

# =======================
# Main
# =======================
def main():
    parser = argparse.ArgumentParser(description="Scrape Tempo.co rubrik tertentu (tanpa batas halaman/artikel).")
    parser.add_argument("--out", default="news_tempo_hukum_last3y.csv", help="Path CSV output")
    parser.add_argument("--rubric", default="hukum", help="Nama rubrik (default: hukum)")
    parser.add_argument("--since", default=None, help="YYYY-MM-DD awal (default: 3 tahun sebelum hari ini, Asia/Makassar)")
    parser.add_argument("--until", default=None, help="YYYY-MM-DD akhir (default: hari ini, Asia/Makassar)")
    parser.add_argument("--no-date-filter", action="store_true", help="Nonaktifkan penyaringan tanggal (ambil semua)")
    parser.add_argument("--checkpoint-every", type=int, default=300, help="Simpan CSV setiap N artikel")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    tz_mks = timezone(timedelta(hours=8))
    now_local = datetime.now(tz=tz_mks)

    if args.no_date_filter:
        since_local = None
        until_local = None
    else:
        until_local = datetime.fromisoformat(args.until).replace(tzinfo=tz_mks) if args.until else now_local
        since_local = datetime.fromisoformat(args.since).replace(tzinfo=tz_mks) if args.since else (until_local - timedelta(days=365*2))
        logging.info(f"Filter tanggal (Asia/Makassar): {since_local.date()} s.d. {until_local.date()}")

    rubric = args.rubric.strip("/").lower()
    global TEMPO_ART_RE
    TEMPO_ART_RE = re.compile(rf"^/{re.escape(rubric)}/[^/?#]+-\d{{6,}}$", re.I)

    session = new_session()

    logging.info(f"[{rubric}] mulai discovery tanpa batas halaman…")
    cand_urls = collect_urls_unlimited(session, rubric)
    logging.info(f"Total kandidat URL: {len(cand_urls)}")

    rows = []
    kept = 0
    for i, u in enumerate(cand_urls, 1):
        try:
            art = scrape_article_tempo(session, u)

            if not args.no_date_filter:
                iso = art.get("released_iso")
                if not iso:
                    time.sleep(DELAY)
                    continue

                utc_dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))

                # Tambahan agar Pylance tahu variabel pasti bukan None
                assert since_local is not None and until_local is not None, "since/until_local None"

                since_utc = since_local.astimezone(timezone.utc)
                until_utc = until_local.astimezone(timezone.utc)

                if not (since_utc <= utc_dt <= until_utc):
                    time.sleep(DELAY)
                    continue

            rows.append(art)
            kept += 1

            if kept % args.checkpoint_every == 0:
                save_rows_to_csv(rows, args.out)
                logging.info(f"Checkpoint → {args.out} (rows={len(rows)})")

            logging.info(f"[keep {kept}/{i}] {u}")
            time.sleep(DELAY)

        except Exception as e:
            logging.warning(f"  ! Gagal {u}: {e}")
            time.sleep(DELAY)

    save_rows_to_csv(rows, args.out)
    logging.info(f"✔ Selesai. Tersimpan {len(rows)} artikel → {args.out}")
    logging.info("Catatan: untuk rubrik lain, jalankan --rubric=<nama> (mis. politik, nasional, metro, bisnis, dunia).")

if __name__ == "__main__":
    main()