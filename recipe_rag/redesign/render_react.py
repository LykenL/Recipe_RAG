"""Render mockup-react.html sections to PNG."""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 2200, "height": 1600}, device_scale_factor=2)
    pg.goto((HERE / "mockup-react.html").as_uri())
    pg.wait_for_timeout(2600)
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(400)
    for sel, name in [("s1", "05-react-empty.png"), ("s2", "06-react-chat.png"), ("mobile", "07-react-mobile.png")]:
        pg.query_selector(f"#{sel}").screenshot(path=str(HERE / name))
        print("wrote", name)
    print(pg.evaluate("()=>{const c=document.querySelector('#mobile .m-canvas');return [c.scrollHeight,c.clientHeight]}"))
    b.close()
