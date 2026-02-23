"""Capture fixed pages dark mode screenshots."""
from playwright.sync_api import sync_playwright
import os, time

BASE = "http://localhost:5001"
OUT = os.path.dirname(os.path.abspath(__file__))

PAGES = [
    ("/sellers", "sellers-fix"),
    ("/url-scraper", "url-scraper-fix"),
    ("/video-transcripts", "video-transcripts-fix"),
]

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path, name in PAGES:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=15000)
            time.sleep(1)
            page.evaluate("""() => {
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            }""")
            time.sleep(0.5)
            page.screenshot(path=os.path.join(OUT, f"{name}-dark-desktop.png"), full_page=False)
            print(f"  Captured: {name}-dark-desktop.png")
            page.close()
        browser.close()

if __name__ == "__main__":
    capture()
