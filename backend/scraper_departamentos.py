"""
Scraper avanzado: navega la UI de ONPE por cada departamento
e intercepta las llamadas por departamento para presidencial.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://resultadoelectoral.onpe.gob.pe"
API_BASE = f"{BASE}/presentacion-backend"

# Mapeo de codigos de distrito ONPE a nombres de departamento
DISTRITOS = {
    1: "AMAZONAS", 2: "ANCASH", 3: "APURIMAC", 4: "AREQUIPA",
    5: "AYACUCHO", 6: "CAJAMARCA", 7: "CALLAO", 8: "CUSCO",
    9: "HUANCAVELICA", 10: "HUANUCO", 11: "ICA", 12: "JUNIN",
    13: "LA LIBERTAD", 14: "LAMBAYEQUE", 15: "LIMA METROPOLITANA",
    16: "LIMA PROVINCIAS", 17: "LORETO", 18: "MADRE DE DIOS",
    19: "MOQUEGUA", 20: "PASCO", 21: "PIURA", 22: "PUNO",
    23: "SAN MARTIN", 24: "TACNA", 25: "TUMBES", 26: "UCAYALI",
}

captured_by_district = {}


def should_capture(url: str) -> bool:
    return "presentacion-backend" in url and "resumen-general" in url


async def scrape_presidencial_by_department():
    """
    Navega la pagina de presidencial en ONPE e intercepta las llamadas
    para cada departamento haciendo click en el selector de distrito.
    """
    all_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        # Capturar todas las respuestas JSON
        responses = {}

        async def on_response(response):
            if not should_capture(response.url):
                return
            try:
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                body = await response.json()
                responses[response.url] = body
            except Exception:
                pass

        page.on("response", on_response)

        print("[1] Cargando pagina presidencial...")
        await page.goto(f"{BASE}/main/presidenciales", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        print(f"  Capturadas {len(responses)} respuestas iniciales")

        # Buscar selector de distrito/departamento
        # El Angular app deberia tener un dropdown para cambiar el ambito
        selectors_to_try = [
            'mat-select',
            '[formcontrolname="distrito"]',
            '[formcontrolname="distritoElectoral"]',
            'select',
            '.selector-distrito',
            '[placeholder*="Distrito"]',
            '[placeholder*="Departamento"]',
        ]

        selector_found = None
        for sel in selectors_to_try:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"  Selector encontrado: {sel} ({count} elementos)")
                selector_found = sel
                break

        if selector_found:
            print("[2] Intentando navegar por departamentos via selector...")
            # Listar las opciones del selector
            if selector_found == 'mat-select':
                # Abrir el mat-select
                await page.locator('mat-select').first.click()
                await asyncio.sleep(1)
                options = await page.locator('mat-option').all()
                print(f"  {len(options)} opciones encontradas")

                for i, opt in enumerate(options[:27]):
                    try:
                        text = await opt.text_content()
                        print(f"  Seleccionando: {text.strip()}")
                        await opt.click()
                        await asyncio.sleep(2)
                        # Reabrir para la siguiente opcion
                        if i < len(options) - 1:
                            await page.locator('mat-select').first.click()
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"  Error en opcion {i}: {e}")
        else:
            print("  No se encontro selector de departamento en presidencial")

        # Guardar todas las respuestas capturadas
        all_data["presidencial_navigation"] = responses

        # Ahora navegar la pagina de senado y hacer lo mismo
        responses2 = {}

        async def on_response2(response):
            if not should_capture(response.url):
                return
            try:
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                body = await response.json()
                responses2[response.url] = body
            except Exception:
                pass

        page.on("response", on_response2)

        print("\n[3] Cargando pagina senado nacional...")
        await page.goto(f"{BASE}/main/senadores-distrito-nacional-unico", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        print(f"  Capturadas {len(responses2)} respuestas")
        all_data["senado_nacional_navigation"] = responses2

        await browser.close()

    # Guardar
    out = DATA_DIR / "navigation_capture.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {out}")
    print(f"Endpoints presidencial: {len(all_data.get('presidencial_navigation', {}))}")
    print(f"Endpoints senado: {len(all_data.get('senado_nacional_navigation', {}))}")

    # Mostrar URLs capturadas
    for section, data in all_data.items():
        print(f"\n--- {section} ---")
        for url in sorted(data.keys()):
            items = data[url].get("data", [])
            n = len(items) if isinstance(items, list) else "dict"
            print(f"  ({n}) {url}")

    return all_data


if __name__ == "__main__":
    asyncio.run(scrape_presidencial_by_department())
