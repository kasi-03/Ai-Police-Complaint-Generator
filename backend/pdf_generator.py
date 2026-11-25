from playwright.sync_api import sync_playwright
import os
import time


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
# Fallback to localhost for PDF generation when BASE_URL might not be accessible
LOCAL_URL = "http://127.0.0.1:5000"


def save_page_as_pdf(url, output_path, max_retries=3):
    """Save a webpage as PDF using Playwright with retry logic."""
    last_error = None

    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--no-first-run',
                        '--no-zygote',
                        '--single-process'
                    ]
                )
                page = browser.new_page()

                # Navigate and wait for content to load
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait a bit for any dynamic content
                page.wait_for_timeout(1500)

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
                return  # Success

        except Exception as e:
            last_error = e
            print(f"PDF generation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue

    raise last_error


def generate_telugu_pdf(filename, complaint_id):
    """Generate Telugu PDF for a complaint."""
    # Try BASE_URL first, fallback to LOCAL_URL
    for base_url in [BASE_URL, LOCAL_URL]:
        try:
            url = f"{base_url}/view_telugu/{complaint_id}"
            save_page_as_pdf(url, filename)
            return
        except Exception as e:
            print(f"Failed with {base_url}: {e}")
            continue
    raise Exception("All URL attempts failed for Telugu PDF generation")


def generate_english_pdf(filename, complaint_id):
    """Generate English PDF for a complaint."""
    # Try BASE_URL first, fallback to LOCAL_URL
    for base_url in [BASE_URL, LOCAL_URL]:
        try:
            url = f"{base_url}/view_english/{complaint_id}"
            save_page_as_pdf(url, filename)
            return
        except Exception as e:
            print(f"Failed with {base_url}: {e}")
            continue
    raise Exception("All URL attempts failed for English PDF generation")