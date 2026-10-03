import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright
import time

def test_smart_fill():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        page.goto("https://job-boards.greenhouse.io/canonical/jobs/5569916")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 1. Base standard fields
        def fill_sel(sel, val):
            try:
                el = page.query_selector(sel)
                if el and not el.input_value():
                    el.fill(val)
            except Exception:
                pass

        fill_sel("input#first_name, input[name='first_name']", "Udaya Lakshmi")
        fill_sel("input#last_name, input[name='last_name']", "Boddu")
        fill_sel("input#email, input[name='email']", "udayalakshmiboddu83@gmail.com")
        fill_sel("input#phone, input[name='phone']", "9390299690")
        fill_sel("input#country, input[name='country']", "India")
        fill_sel("input#school--0, input[name*='school']", "Jawaharlal Nehru Technological University Kakinada (JNTUK)")
        fill_sel("input#degree--0, input[name*='degree']", "Bachelor of Technology - B.Tech")
        fill_sel("input#discipline--0, input[name*='discipline']", "Electrical and Electronics Engineering")

        # 2. Attach resume
        file_inp = page.query_selector("input[type='file'], input#resume_file")
        if file_inp:
            file_inp.set_input_files("data/resume.pdf")

        # 3. Intelligent custom question filler
        text_controls = page.query_selector_all("input[type='text'], textarea")
        for ctrl in text_controls:
            try:
                if ctrl.input_value():
                    continue
                cid = ctrl.get_attribute("id") or ""
                cname = ctrl.get_attribute("name") or ""
                lbl_el = page.query_selector(f"label[for='{cid}']") if cid else None
                lbl = (lbl_el.inner_text() if lbl_el else cname).lower()

                if "math" in lbl:
                    ctrl.fill("Top 10% / Grade A in Mathematics")
                elif "native language" in lbl or "language" in lbl:
                    ctrl.fill("Excellent / Fluent in English and Telugu")
                elif "degree" in lbl or "gpa" in lbl or "result" in lbl:
                    ctrl.fill("B.Tech in Electrical & Electronics Engineering (EEE), JNTUK, 2024 Graduate with CGPA 7.4 / 10")
                elif "country" in lbl or "work" in lbl or "location" in lbl or "nationality" in lbl:
                    ctrl.fill("India")
                elif "gender" in lbl:
                    ctrl.fill("Female")
                elif "race" in lbl or "ethnicity" in lbl:
                    ctrl.fill("Asian / Indian")
                elif "linkedin" in lbl:
                    ctrl.fill("https://www.linkedin.com/in/udaya-lakshmi-boddu")
                elif "website" in lbl or "github" in lbl or "portfolio" in lbl:
                    ctrl.fill("https://github.com/udayalakshmiboddu")
                elif "experience" in lbl or "describe" in lbl:
                    ctrl.fill("2024 Engineering Graduate from JNTUK with practical academic project experience in Embedded Systems, IoT, C programming, and SQL data automation.")
                elif "agree" in lbl or "confirm" in lbl or "meet" in lbl:
                    ctrl.fill("Yes, I agree and confirm.")
                elif ctrl.get_attribute("required") is not None:
                    ctrl.fill("Yes / Applicable as per graduate profile")
            except Exception as e:
                print("Error filling custom field:", e)

        # 4. Handle custom selects / dropdown buttons (Greenhouse search selects)
        for custom_sel in page.query_selector_all("div[class*='select'], div[role='combobox']"):
            try:
                btn = custom_sel.query_selector("button, div[class*='control']")
                if btn and ("select" in btn.inner_text().lower() or not btn.inner_text().strip()):
                    btn.click()
                    time.sleep(0.5)
                    opt = page.query_selector("div[role='option'], div[class*='option']")
                    if opt:
                        opt.click()
            except Exception:
                pass

        # Check required checkboxes
        for cb in page.query_selector_all("input[type='checkbox']"):
            try:
                if not cb.is_checked():
                    cb.check()
            except Exception:
                pass

        print("Form filled! Checking remaining empty required fields...")
        unfilled_req = []
        for inp in page.query_selector_all("input, select, textarea"):
            req = inp.get_attribute("required") is not None
            val = inp.input_value() if hasattr(inp, "input_value") else ""
            if req and not val:
                unfilled_req.append(inp.get_attribute("name") or inp.get_attribute("id"))

        print(f"Unfilled required count: {len(unfilled_req)} -> {unfilled_req}")
        browser.close()

if __name__ == "__main__":
    test_smart_fill()
