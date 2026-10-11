"""Usage: .venv/bin/python scripts/check_pages.py [http://localhost:8501]
Headless check: render each Beemer page, report Streamlit exceptions, save full-page screenshots."""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
PAGES = [("", "01-cockpit"), ("screener", "02-screener"), ("company?symbol=INFY", "03-company-infosys"),
         ("company?symbol=SWIGGY", "04-company-swiggy"), ("learn", "05-academy")]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "screenshots")
ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    for path, name in PAGES:
        pg.goto(f"{BASE}/{path}", wait_until="networkidle", timeout=120000)
        pg.wait_for_selector(".bm-foot", timeout=120000)
        pg.wait_for_timeout(3000)
        errs = pg.locator('[data-testid="stException"]').all_inner_texts()
        if errs:
            ok = False; print("ERROR on", path, errs[0][:1500])
        h = pg.evaluate("() => { const e = document.querySelector('[data-testid=\"stMain\"]') || document.querySelector('section.main'); return e ? e.scrollHeight : document.body.scrollHeight; }")
        pg.set_viewport_size({"width": 1440, "height": min(int(h) + 40, 16000)})
        pg.wait_for_timeout(2500)
        pg.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
        pg.set_viewport_size({"width": 1440, "height": 900})
        print("ok" if not errs else "ERR", path)
    b.close()
sys.exit(0 if ok else 1)
