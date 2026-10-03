import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page()
    page.goto("https://job-boards.greenhouse.io/canonical/jobs/5569916")
    page.wait_for_load_state("domcontentloaded")
    
    print("Page Title:", page.title())
    
    inputs = page.query_selector_all("input, select, textarea")
    print(f"Total form controls: {len(inputs)}")
    for inp in inputs:
        name = inp.get_attribute("name") or inp.get_attribute("id") or ""
        itype = inp.get_attribute("type") or inp.evaluate("el => el.tagName.toLowerCase()")
        req = inp.get_attribute("required") is not None or inp.get_attribute("aria-required") == "true"
        label_text = ""
        try:
            inp_id = inp.get_attribute("id")
            if inp_id:
                lbl = page.query_selector(f"label[for='{inp_id}']")
                if lbl:
                    label_text = lbl.inner_text().strip().replace("\n", " ")
        except Exception:
            pass
        print(f"  - [{itype}] name={name} required={req} label='{label_text[:50]}'")
    browser.close()
