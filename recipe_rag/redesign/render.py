"""Render redesign/mockup.html sections to PNG using headless Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = (HERE / "mockup.html").as_uri()
TARGETS = [
    ("s1", "01-empty-state.png", 2),
    ("s2", "02-conversation.png", 2),
    ("mobile", "03-mobile.png", 3),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2200, "height": 1400}, device_scale_factor=2)
    page.goto(URL)
    page.wait_for_timeout(2500)  # webfonts
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(500)
    for sel, name, scale in TARGETS:
        el = page.query_selector(f"#{sel}")
        el.screenshot(path=str(HERE / name), scale="css" if scale == 1 else None)
        print("wrote", name)
    browser.close()
