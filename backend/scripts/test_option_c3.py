"""
Intercept the exact API call ONPE makes when selecting a department on presidential page.
"""
import asyncio
from playwright.async_api import async_playwright

ONPE_URL = "https://resultadoelectoral.onpe.gob.pe/main/resumen"

captured_urls = []

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Capture ALL requests (not just responses) from the backend API
        async def on_request(request):
            if "presentacion-backend" in request.url:
                captured_urls.append(request.url)

        async def on_response(response):
            if "presentacion-backend" in response.url:
                try:
                    data = await response.json()
                    if data.get("success") and len(data.get("data", [])) > 0:
                        print(f"[HIT] {response.url[-120:]}")
                        print(f"      records={len(data['data'])} top={data['data'][0].get('nombreAgrupacionPolitica','?')[:40]}")
                except:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        print("Loading ONPE page...")
        try:
            await page.goto(ONPE_URL, wait_until="domcontentloaded", timeout=30000)
        except:
            pass

        # Wait for Angular to hydrate
        print("Waiting for Angular to boot...")
        await asyncio.sleep(10)

        print(f"\nTotal API requests made so far: {len(captured_urls)}")
        for url in captured_urls[:20]:
            print(f"  {url[-120:]}")

        # Try to find and interact with the department selector
        print("\nLooking for department dropdown...")

        # Angular Material select with formcontrolname="department"
        selects = await page.query_selector_all("mat-select")
        print(f"  mat-select elements: {len(selects)}")

        for i, sel in enumerate(selects):
            aria_label = await sel.get_attribute("aria-labelledby") or ""
            val = await sel.inner_text()
            print(f"  [{i}] text='{val[:30]}' aria={aria_label[:30]}")

        # Try clicking on the second mat-select (department)
        if len(selects) >= 2:
            print("\nClicking department dropdown (index 1)...")
            await selects[1].click()
            await asyncio.sleep(2)

            # Look for options in the CDK overlay
            options = await page.query_selector_all("mat-option")
            print(f"  mat-option elements found: {len(options)}")
            for i, opt in enumerate(options[:10]):
                txt = await opt.inner_text()
                print(f"    [{i}] {txt}")

            # Click ANCASH
            ancash_opt = None
            for opt in options:
                txt = await opt.inner_text()
                if "NCASH" in txt.upper() or "NCAS" in txt.upper():
                    ancash_opt = opt
                    break

            if ancash_opt:
                print("\nClicking ÁNCASH...")
                initial_count = len(captured_urls)
                await ancash_opt.click()
                await asyncio.sleep(5)

                new_urls = captured_urls[initial_count:]
                print(f"\nNew API requests after selecting ÁNCASH ({len(new_urls)}):")
                for url in new_urls:
                    print(f"  {url}")
            else:
                print("  ANCASH option not found")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
