from playwright.sync_api import sync_playwright
import os


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")


def save_page_as_pdf(url, output_path):
    """Save a webpage as PDF using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate and wait for content to load
        page.goto(url, wait_until="networkidle")

        # Wait a bit for any dynamic content
        page.wait_for_timeout(1000)

        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={
                "top": "10mm",
                "bottom": "10mm",
                "left": "10mm",
                "right": "10mm"
            }
        )
        browser.close()


def generate_telugu_pdf(filename, complaint_id):
    """Generate Telugu PDF for a complaint."""
    url = f"{BASE_URL}/view_telugu/{complaint_id}"
    save_page_as_pdf(url, filename)


def generate_english_pdf(filename, complaint_id):
    """Generate English PDF for a complaint."""
    url = f"{BASE_URL}/view_english/{complaint_id}"
    save_page_as_pdf(url, filename)