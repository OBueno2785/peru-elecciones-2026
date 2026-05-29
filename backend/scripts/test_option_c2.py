"""
Option C v2: Captura todas las llamadas API de ONPE usando intercepcion de red.
"""
import asyncio
import json
from playwright.async_api import async_playwright

ONPE_URL = "https://resultadoelectoral.onpe.gob.pe/main/resumen"
captured = {}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Registrar listener ANTES de navegar
        async def handle_response(response):
            url = response.url
            if "presentacion-backend" in url:
                try:
                    data = await response.json()
                    captured[url] = data
                except:
                    pass

        page.on("response", handle_response)

        print("Navegando a ONPE (puede tardar 30s)...")
        try:
            await page.goto(ONPE_URL, wait_until="load", timeout=45000)
        except Exception as e:
            print(f"  timeout/error: {e}")

        # Esperar que cargue el contenido dinamico
        await asyncio.sleep(8)

        print(f"URLs de presentacion-backend capturadas: {len(captured)}")
        for url in sorted(captured.keys()):
            data = captured[url]
            records = len(data.get("data", []))
            success = data.get("success")
            print(f"  [{success}|{records:3d}] {url[60:]}")

        # Guardar todo
        with open("onpe_all_captured.json", "w", encoding="utf-8") as f:
            json.dump({url: {"success": v.get("success"), "records": len(v.get("data", []))}
                       for url, v in captured.items()}, f, indent=2, ensure_ascii=False)

        # Ahora intentar hacer click en algun departamento
        print("\nBuscando elementos de departamento...")
        # Buscar SVG paths o elementos con nombre de departamento
        content = await page.content()
        print(f"  Pagina cargada: {len(content)} chars")
        print(f"  Title: {await page.title()}")

        # Guardar HTML completo
        with open("onpe_full.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("  HTML completo guardado en onpe_full.html")

        # Buscar links/botones de departamento
        for dep in ["Lima", "Callao", "Arequipa"]:
            elements = await page.query_selector_all(f"text={dep}")
            if elements:
                print(f"  Encontrado elemento con texto '{dep}': {len(elements)} elementos")

        # Buscar en el SVG del mapa
        svg_elements = await page.query_selector_all("svg path, svg g")
        print(f"  Elementos SVG path/g: {len(svg_elements)}")

        # Capturar snapshot de accesibilidad
        # await page.screenshot(path="onpe_screenshot.png")
        # print("  Screenshot guardado")

        await browser.close()
        print("\nDone.")

if __name__ == "__main__":
    asyncio.run(main())
