#!/usr/bin/env python3
"""Headless smoke test: render every Beemer page with Streamlit's AppTest and fail on any exception.
Run from the repo root:  python scripts/smoke_test.py   (used by CI and `make test`)"""
import os, sys
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
failed = False
for page in ["views/cockpit.py", "views/screener.py", "views/company.py", "views/learn.py"]:
    at = AppTest.from_file(os.path.join(ROOT, "app", "main.py"), default_timeout=180)
    at.run()
    if page != "views/cockpit.py":
        at.switch_page(page).run()
    errs = [e.value for e in at.exception]
    print(f"{'✗' if errs else '✓'} {page}: {len(at.markdown)} markdown blocks" + (f"  errors: {errs}" if errs else ""))
    failed |= bool(errs)
sys.exit(1 if failed else 0)
