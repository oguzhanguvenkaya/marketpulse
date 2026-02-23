"""Capture dark mode screenshots of all pages for visual review."""
from playwright.sync_api import sync_playwright
import os, time

BASE = "http://localhost:5001"
OUT = os.path.dirname(os.path.abspath(__file__))

PAGES = [
    ("/", "dashboard"),
    ("/products", "products"),
    ("/sellers", "sellers"),
    ("/ads", "ads"),
    ("/url-scraper", "url-scraper"),
    ("/video-transcripts", "video-transcripts"),
    ("/json-editor", "json-editor"),
    ("/category-explorer", "category-explorer"),
]

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for mode in ["light", "dark"]:
            for path, name in PAGES:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=15000)
                time.sleep(1)

                if mode == "dark":
                    # Toggle dark mode
                    page.evaluate("""() => {
                        document.documentElement.classList.add('dark');
                        localStorage.setItem('theme', 'dark');
                    }""")
                    time.sleep(0.5)

                fname = f"{name}-{mode}-desktop.png"
                page.screenshot(path=os.path.join(OUT, fname), full_page=False)
                print(f"  Captured: {fname}")

                # Mobile viewport
                page.set_viewport_size({"width": 390, "height": 844})
                time.sleep(0.3)
                fname_m = f"{name}-{mode}-mobile.png"
                page.screenshot(path=os.path.join(OUT, fname_m), full_page=False)
                print(f"  Captured: {fname_m}")

                page.close()

        browser.close()
    print("\nDone! All screenshots saved.")

if __name__ == "__main__":
    capture_all()
