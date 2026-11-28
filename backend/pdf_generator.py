from playwright.sync_api import sync_playwright
import os
import time


# Set Playwright browsers path for container environments
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright")


def save_html_as_pdf(html_content, output_path, max_retries=3):
    """Render an HTML string to PDF using Playwright (no HTTP round-trip needed)."""
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

                # Set base URL so relative links to static assets resolve
                page.set_content(
                    html_content,
                    wait_until="networkidle",
                    timeout=30000
                )

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


def generate_telugu_pdf(filename, complaint_id, html_content):
    """Generate Telugu PDF for a complaint from rendered HTML."""
    return save_html_as_pdf(html_content, filename)


def generate_english_pdf(filename, complaint_id, html_content):
    """Generate English PDF for a complaint from rendered HTML."""
    return save_html_as_pdf(html_content, filename)
