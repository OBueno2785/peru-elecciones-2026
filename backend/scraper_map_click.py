"""
Navega la UI de ONPE, hace clic en el mapa por cada departamento
y captura los endpoints con resultados por departamento.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://resultadoelectoral.onpe.gob.pe"

DISTRITOS_NOMBRES = {
    10000: "AMAZONAS", 20000: "ANCASH", 30000: "APURIMAC",
    40000: "AREQUIPA", 50000: "AYACUCHO", 60000: "CAJAMARCA",
    70000: "CALLAO", 80000: "CUSCO", 90000: "HUANCAVELICA",
    100000: "HUANUCO", 110000: "ICA", 120000: "JUNIN",
    130000: "LA LIBERTAD", 140000: "LAMBAYEQUE", 150000: "LIMA METROPOLITANA",
    160000: "LIMA PROVINCIAS", 170000: "LORETO", 180000: "MADRE DE DIOS",
    190000: "MOQUEGUA", 200000: "PASCO", 210000: "PIURA", 220000: "PUNO",
    230000: "SAN MARTIN", 240000: "TACNA", 250000: "TUMBES", 260000: "UCAYALI",
}

# ubigeo nivel01 -> codigo de distrito electoral ONPE (1-26)
UBIGEO_TO_DISTRITO = {
    10000: 1, 20000: 2, 30000: 3, 40000: 4, 50000: 5,
    60000: 6, 70000: 7, 80000: 8, 90000: 9, 100000: 10,
    110000: 11, 120000: 12, 130000: 13, 140000: 14,
    150000: 15, 160000: 16, 170000: 17, 180000: 18,
    190000: 19, 200000: 20, 210000: 21, 220000: 22,
    230000: 23, 240000: 24, 250000: 25, 260000: 26,
}


async def capture_responses(page, wait_time=3):
    """Captura todas las respuestas JSON de una pagina."""
    responses = {}

    async def on_resp(r):
        if "presentacion-backend" not in r.url:
            return
        try:
            ct = r.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = await r.json()
            responses[r.url] = body
        except Exception:
            pass

    page.on("response", on_resp)
    await asyncio.sleep(wait_time)
    page.remove_listener("response", on_resp)
    return responses


async def try_fetch_by_ubigeo(client_page, all_data: dict):
    """
    Intenta fetchear directamente los datos de candidatos por ubigeo departamento.
    La API usa idAmbitoGeografico para el nivel (1=departamento) y ubigeoNivel01.
    """
    import httpx
    HEADERS = {
        "Accept": "application/json",
        "Referer": f"{BASE}/main/presidenciales",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    }
    BACKEND = f"{BASE}/presentacion-backend"

    ubigeos = list(DISTRITOS_NOMBRES.keys())

    with httpx.Client(follow_redirects=True) as c:
        # Init session
        c.get(f"{BASE}/", headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})

        print("\n[TEST] Buscando endpoint por ubigeo departamento...")
        for ubigeo in ubigeos[:5]:  # probar con los primeros 5
            nombre = DISTRITOS_NOMBRES[ubigeo]
            dist = UBIGEO_TO_DISTRITO[ubigeo]

            urls_test = [
                f"{BACKEND}/resumen-general/participantes?idEleccion=10&tipoFiltro=ambito_geografico&idAmbitoGeografico=1&ubigeoNivel01={ubigeo}",
                f"{BACKEND}/resumen-general/participantes?idEleccion=10&tipoFiltro=ambito_geografico&ubigeoNivel01={ubigeo}",
                f"{BACKEND}/resumen-general/participantes?idEleccion=10&tipoFiltro=departamento&ubigeo={ubigeo}",
                f"{BACKEND}/resumen-general/participantes?idEleccion=10&idUbigeoDepartamento={ubigeo}&tipoFiltro=eleccion",
                f"{BACKEND}/resumen-general/participantes?idEleccion=10&idUbigeoNivel01={ubigeo}",
            ]

            for url in urls_test:
                r = c.get(url, headers=HEADERS, timeout=10)
                ct = r.headers.get("content-type", "")
                if "json" in ct:
                    d = r.json()
                    items = d.get("data", [])
                    if isinstance(items, list) and len(items) > 0:
                        print(f"  ENCONTRADO para {nombre}: {url[-70:]}")
                        all_data[url] = d
                        break
                elif r.status_code not in [204]:
                    pass  # silencio para HTML

    return all_data


async def main():
    all_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        # Capturar respuestas globalmente
        global_responses = {}

        async def global_on_resp(r):
            if "presentacion-backend" not in r.url:
                return
            if "mapa-calor" in r.url or "participantes" in r.url or "totales" in r.url:
                try:
                    ct = r.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    body = await r.json()
                    global_responses[r.url] = body
                    if "participantes" in r.url:
                        items = body.get("data", [])
                        n = len(items) if isinstance(items, list) else "dict"
                        print(f"  [{n}] {r.url[-80:]}")
                except Exception:
                    pass

        page.on("response", global_on_resp)

        # Navegar a presidencial
        print("[1] Cargando presidencial...")
        await page.goto(f"{BASE}/main/presidenciales", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        # Buscar elementos clickeables del mapa (SVG paths, divs con ubigeo)
        print("[2] Buscando elementos del mapa...")
        map_elements = await page.evaluate("""
            () => {
                // Buscar elementos SVG del mapa
                const svgs = document.querySelectorAll('svg path, svg g[data-ubigeo], [class*="region"], [class*="departamento"], [data-ubigeo]');
                const results = [];
                for (const el of svgs) {
                    const ubigeo = el.getAttribute('data-ubigeo') || el.getAttribute('id') || '';
                    const cls = el.className || '';
                    if (ubigeo || cls.includes('region') || cls.includes('depart')) {
                        results.push({
                            tag: el.tagName,
                            id: el.id || '',
                            ubigeo: ubigeo,
                            class: typeof cls === 'string' ? cls.substring(0, 50) : '',
                        });
                    }
                }
                return results.slice(0, 30);
            }
        """)
        print(f"  Elementos encontrados: {len(map_elements)}")
        for el in map_elements[:5]:
            print(f"    {el}")

        # Buscar y hacer clic en las regiones del mapa AMCharts
        print("[3] Buscando mapa AMCharts...")
        amcharts_info = await page.evaluate("""
            () => {
                // AMCharts usa elementos con id del ubigeo
                const paths = document.querySelectorAll('[id^="PE-"], [id*="department"], path[id]');
                const results = [];
                for (const p of paths) {
                    results.push({tag: p.tagName, id: p.id, class: p.className?.substring(0, 50) || ''});
                }
                return results.slice(0, 30);
            }
        """)
        print(f"  Elementos AMCharts: {len(amcharts_info)}")
        for el in amcharts_info[:10]:
            print(f"    {el}")

        # Buscar cualquier elemento interactivo del mapa
        print("[4] Buscando region clickeable...")
        clickable = await page.evaluate("""
            () => {
                const all = document.querySelectorAll('*');
                const candidates = [];
                for (const el of all) {
                    const c = el.className || '';
                    const id = el.id || '';
                    const cs = typeof c === 'string' ? c : '';
                    if (cs.includes('region') || cs.includes('mapa') || cs.includes('map') ||
                        cs.includes('departamento') || id.includes('PE-') || id.includes('region')) {
                        candidates.push({
                            tag: el.tagName,
                            id: id.substring(0, 40),
                            class: cs.substring(0, 60),
                            text: (el.textContent || '').trim().substring(0, 30),
                        });
                    }
                }
                return candidates.slice(0, 20);
            }
        """)
        print(f"  Candidatos clickeables: {len(clickable)}")
        for el in clickable[:10]:
            print(f"    {el}")

        await browser.close()

    # Guardar datos capturados
    all_data.update(global_responses)

    # Buscar por ubigeo via HTTP directo
    all_data = await try_fetch_by_ubigeo(None, all_data)

    out = DATA_DIR / "map_click_capture.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {out}")
    print(f"Total endpoints: {len(all_data)}")
    for url in sorted(all_data.keys()):
        items = all_data[url].get("data", [])
        n = len(items) if isinstance(items, list) else "dict"
        print(f"  ({n}) {url[-90:]}")


if __name__ == "__main__":
    asyncio.run(main())
