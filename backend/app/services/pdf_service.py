import asyncio

from playwright.async_api import async_playwright


async def generate_pdf(html_content: str, output_path: str):
    """Render saved HTML to PDF. Do not wait for networkidle — Google Fonts
    and other CDNs often never idle inside Docker and used to 500 /analyze.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        try:
            await page.set_content(
                html_content,
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await page.emulate_media(media="print")
            await asyncio.sleep(0.4)
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                margin={"top": "0cm", "bottom": "0cm", "left": "0cm", "right": "0cm"},
                prefer_css_page_size=True,
                landscape=True,
            )
        finally:
            await browser.close()


async def generate_pdf_safe(html_content: str, output_path: str) -> bool:
    """PDF is optional. HTML reports must still succeed if Chromium times out."""
    try:
        await generate_pdf(html_content, output_path)
        return True
    except Exception as exc:
        print(f"--- WARNING: PDF generation failed for {output_path}: {exc} ---")
        return False
