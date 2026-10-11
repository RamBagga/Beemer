"""Single full-page screenshot. Usage: .venv/bin/python scripts/shot.py URL OUT.png [width] [wait_selector] [wait_ms]"""
import sys, asyncio
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
wait = sys.argv[4] if len(sys.argv) > 4 else None
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": 900}, device_scale_factor=1)
    pg.goto(url, wait_until="networkidle", timeout=120000)
    if wait:
        pg.wait_for_selector(wait, timeout=120000)
    pg.wait_for_timeout(int(sys.argv[5]) if len(sys.argv) > 5 else 1500)
    pg.screenshot(path=out, full_page=True)
    b.close()
