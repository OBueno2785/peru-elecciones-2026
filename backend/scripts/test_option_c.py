"""
Option C: Playwright scraper para capturar llamadas API de ONPE por departamento presidencial.
Navega a la SPA de ONPE, selecciona cada departamento y captura las respuestas JSON.
"""
import asyncio
import json
from playwright.async_api import async_playwright

ONPE_URL = "https://resultadoelectoral.onpe.gob.pe/main/resumen"

DEPARTAMENTOS = [
    "AMAZONAS", "ANCASH", "APURIMAC", "AREQUIPA", "AYACUCHO",
    "CAJAMARCA", "CALLAO", "CUSCO", "HUANCAVELICA", "HUANUCO",
    "ICA", "JUNIN", "LA LIBERTAD", "LAMBAYEQUE", "LIMA",
    "LORETO", "MADRE DE DIOS", "MOQUEGUA", "PASCO", "PIURA",
    "PUNO", "SAN MARTIN", "TACNA", "TUMBES", "UCAYALI",
]

captured = {}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Capturar todas las respuestas JSON de la API de ONPE
        async def handle_response(response):
            url = response.url
            if "presentacion-backend" in url and "presidencial" in url.lower():
                try:
                    data = await response.json()
                    captured[url] = data
                    print(f"  [API] {url[-100:]}")
                    print(f"        success={data.get('success')} records={len(data.get('data', []))}")
                except:
                    pass

        page.on("response", handle_response)

        print("Navegando a ONPE...")
        await page.goto(ONPE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        print(f"\nURLs capturadas en carga inicial: {len(captured)}")
        for url in list(captured.keys())[:5]:
            print(f"  {url[-120:]}")

        # Ver si hay selector de departamento / tipo de eleccion
        print("\nBuscando selectores en la pagina...")
        selectors = await page.query_selector_all("select, [role='listbox'], [role='option']")
        print(f"  select/listbox elements: {len(selectors)}")

        # Buscar botones o tabs de departamento
        buttons = await page.query_selector_all("button")
        print(f"  botones: {len(buttons)}")

        # Buscar el texto "Presidencial" en la pagina
        content = await page.content()
        if "residencial" in content:
            print("  'residencial' encontrado en pagina")
        if "departamento" in content.lower():
            print("  'departamento' encontrado en pagina")

        # Capturar snapshot de la estructura
        title = await page.title()
        print(f"\nTitulo: {title}")

        # Guardar HTML para inspeccion
        with open("onpe_snapshot.html", "w", encoding="utf-8") as f:
            f.write(content[:50000])  # primeros 50k chars
        print("HTML guardado en onpe_snapshot.html (primeros 50k chars)")

        # Guardar todas las URLs capturadas
        print(f"\n=== TOTAL URLs capturadas: {len(captured)} ===")
        with open("onpe_captured_urls.json", "w", encoding="utf-8") as f:
            json.dump(list(captured.keys()), f, indent=2, ensure_ascii=False)

        # Ver si hay requests con tipoFiltro para presidencial
        for url in captured:
            if "presidencial" in url.lower() or "participantes" in url.lower():
                data = captured[url]
                print(f"\nURL: {url[-100:]}")
                print(f"  records: {len(data.get('data', []))}")
                if data.get("data"):
                    first = data["data"][0]
                    print(f"  primer registro keys: {list(first.keys())[:10]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
