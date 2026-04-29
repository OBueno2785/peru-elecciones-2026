"""
Captura resultados presidenciales por departamento navegando la SPA de ONPE.
Graba TODAS las llamadas a presentacion-backend para cada ubigeo,
luego filtra las que tienen datos per-departamento.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / "data"

BASE = "https://resultadoelectoral.onpe.gob.pe"

DEPARTAMENTOS = {
    10000:  "AMAZONAS",
    20000:  "ANCASH",
    30000:  "APURIMAC",
    40000:  "AREQUIPA",
    50000:  "AYACUCHO",
    60000:  "CAJAMARCA",
    70000:  "CALLAO",
    80000:  "CUSCO",
    90000:  "HUANCAVELICA",
    100000: "HUANUCO",
    110000: "ICA",
    120000: "JUNIN",
    130000: "LA LIBERTAD",
    140000: "LAMBAYEQUE",
    150000: "LIMA METROPOLITANA",
    160000: "LIMA PROVINCIAS",
    170000: "LORETO",
    180000: "MADRE DE DIOS",
    190000: "MOQUEGUA",
    200000: "PASCO",
    210000: "PIURA",
    220000: "PUNO",
    230000: "SAN MARTIN",
    240000: "TACNA",
    250000: "TUMBES",
    260000: "UCAYALI",
}


async def capture_dept(page, ubigeo: int, nombre: str):
    responses = {}

    async def on_resp(r):
        url = r.url
        if "presentacion-backend" not in url:
            return
        if "idEleccion=10" not in url:
            return
        try:
            if r.status != 200:
                return
            ct = r.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = await r.json()
            if body.get("success"):
                responses[url] = body
        except Exception:
            pass

    page.on("response", on_resp)
    try:
        await page.goto(f"{BASE}/main/resumen?ubigeo={ubigeo}",
                        wait_until="networkidle", timeout=25000)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"  timeout: {e}")
    page.remove_listener("response", on_resp)
    return responses


async def main():
    result = {}  # nombre -> {participantes, totales}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        print("Iniciando sesion...")
        await page.goto(BASE, wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)

        for ubigeo, nombre in DEPARTAMENTOS.items():
            print(f"  {nombre} (ubigeo={ubigeo})...", end=" ", flush=True)
            responses = await capture_dept(page, ubigeo, nombre)

            # Mostrar todas las URLs capturadas para diagnostico
            dept_apis = [u for u in responses if "idEleccion=10" in u]
            print(f"{len(dept_apis)} urls presidenciales")
            for u in dept_apis:
                data = responses[u].get("data", [])
                n = len(data) if isinstance(data, list) else "obj"
                print(f"    {u[60:]}  -> {n} items")

            # Buscar participantes per-departamento (tipoFiltro != eleccion o con ubigeo)
            participantes = []
            totales = {}
            for url, body in responses.items():
                data = body.get("data", [])
                if "participantes" in url:
                    # Preferir datos con idUbigeo o tipoFiltro=ambito_geografico sobre tipoFiltro=eleccion
                    if "tipoFiltro=eleccion" not in url or not participantes:
                        if isinstance(data, list) and data:
                            participantes = data
                if "totales" in url:
                    if isinstance(data, dict) and data:
                        totales = data

            if participantes:
                result[nombre] = {
                    "participantes": participantes,
                    "totales": totales,
                }

        await browser.close()

    out = DATA_DIR / "presidencial_distritos.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {out} ({len(result)} departamentos con datos)")

    # Verificar variedad - si todos tienen los mismos candidatos lider, son datos nacionales
    lideres = set()
    for nombre, data in result.items():
        parts = sorted(data["participantes"],
                       key=lambda x: float(x.get("porcentajeVotosValidos", 0)),
                       reverse=True)
        if parts:
            lideres.add(parts[0].get("nombreAgrupacionPolitica", ""))
    print(f"Partidos lider distintos encontrados: {lideres}")
    if len(lideres) == 1:
        print("AVISO: todos los departamentos tienen el mismo lider. Posiblemente son datos nacionales.")


if __name__ == "__main__":
    asyncio.run(main())
