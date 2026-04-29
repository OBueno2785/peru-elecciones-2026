"""
Captura datos por distrito navegando /main/resumen?ubigeo=X para cada departamento.
Obtiene: presidencial nacional, senado regional por distrito, diputados por distrito.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://resultadoelectoral.onpe.gob.pe"

# ubigeo -> (nombre, codigo_distrito_onpe)
DEPARTAMENTOS = {
    10000:  ("AMAZONAS", 1),
    20000:  ("ANCASH", 2),
    30000:  ("APURIMAC", 3),
    40000:  ("AREQUIPA", 4),
    50000:  ("AYACUCHO", 5),
    60000:  ("CAJAMARCA", 6),
    70000:  ("CALLAO", 7),
    80000:  ("CUSCO", 8),
    90000:  ("HUANCAVELICA", 9),
    100000: ("HUANUCO", 10),
    110000: ("ICA", 11),
    120000: ("JUNIN", 12),
    130000: ("LA LIBERTAD", 13),
    140000: ("LAMBAYEQUE", 14),
    150000: ("LIMA METROPOLITANA", 15),
    160000: ("LIMA PROVINCIAS", 16),
    170000: ("LORETO", 17),
    180000: ("MADRE DE DIOS", 18),
    190000: ("MOQUEGUA", 19),
    200000: ("PASCO", 20),
    210000: ("PIURA", 21),
    220000: ("PUNO", 22),
    230000: ("SAN MARTIN", 23),
    240000: ("TACNA", 24),
    250000: ("TUMBES", 25),
    260000: ("UCAYALI", 26),
}


async def capture_for_district(page, ubigeo: int, nombre: str, distrito_cod: int):
    """Navega /main/resumen?ubigeo=X y captura los endpoints por distrito."""
    responses = {}

    async def on_resp(r):
        url = r.url
        if "presentacion-backend" not in url:
            return
        if "participantes" not in url and "totales" not in url:
            return
        try:
            ct = r.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = await r.json()
            if body.get("success"):
                responses[url] = body
        except Exception:
            pass

    page.on("response", on_resp)

    url = f"{BASE}/main/resumen?ubigeo={ubigeo}"
    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"  Timeout: {e}")

    page.remove_listener("response", on_resp)
    return responses


async def main():
    all_data = {
        "meta": {
            "departamentos": {
                str(ubigeo): {"nombre": n, "codigo_distrito": c}
                for ubigeo, (n, c) in DEPARTAMENTOS.items()
            }
        },
        "por_distrito": {},
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # Cargar la SPA primero
        print("Iniciando sesion...")
        await page.goto(BASE, wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)

        # Navegar por cada departamento
        for ubigeo, (nombre, cod) in DEPARTAMENTOS.items():
            print(f"[{cod:2d}] {nombre} (ubigeo={ubigeo})")
            responses = await capture_for_district(page, ubigeo, nombre, cod)

            # Organizar por tipo de eleccion
            distrito_data = {"nombre": nombre, "ubigeo": ubigeo, "codigo_distrito": cod}

            for url, body in responses.items():
                items = body.get("data", [])
                n = len(items) if isinstance(items, list) else "obj"

                # Identificar tipo de eleccion y si es por distrito
                if "idEleccion=10" in url and "tipoFiltro=eleccion" in url:
                    if "participantes" in url:
                        distrito_data["presidencial_participantes"] = items
                    elif "totales" in url:
                        distrito_data["presidencial_totales"] = items
                elif "idEleccion=14" in url:
                    if "participantes" in url:
                        distrito_data["senado_regional_participantes"] = items
                        print(f"    senado_regional: {n} candidatos")
                    elif "totales" in url:
                        distrito_data["senado_regional_totales"] = items
                elif "idEleccion=13" in url:
                    if "participantes" in url:
                        distrito_data["diputados_participantes"] = items
                        print(f"    diputados: {n} candidatos")
                elif "idEleccion=15" in url and "tipoFiltro=eleccion" in url:
                    if "participantes" in url:
                        distrito_data["senado_nacional_participantes"] = items
                elif "idEleccion=12" in url:
                    if "participantes" in url:
                        distrito_data["parlamento_andino_participantes"] = items

            all_data["por_distrito"][ubigeo] = distrito_data

        await browser.close()

    # Guardar
    out = DATA_DIR / "por_distrito.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {out}")
    print(f"Distritos procesados: {len(all_data['por_distrito'])}")

    # Resumen de cobertura
    for ubigeo, data in all_data["por_distrito"].items():
        nombre = data.get("nombre", "?")
        sr = len(data.get("senado_regional_participantes", []))
        dp = len(data.get("diputados_participantes", []))
        print(f"  {nombre}: senado_reg={sr}, diputados={dp}")


if __name__ == "__main__":
    asyncio.run(main())
