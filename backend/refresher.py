"""
Refresca los datos de ONPE cada N minutos usando httpx.
Actualiza los JSON en data/ y señala al cache para reconstruirse.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import httpx

DATA_DIR = Path(__file__).parent / "data"
BASE     = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend"
SPA      = "https://resultadoelectoral.onpe.gob.pe/"
RESUMEN  = "https://resultadoelectoral.onpe.gob.pe/main/resumen"

log = logging.getLogger("refresher")

BROWSER_HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-PE,es;q=0.9",
    "Connection": "keep-alive",
}
API_HDR = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://resultadoelectoral.onpe.gob.pe/main/resumen",
    "Origin": "https://resultadoelectoral.onpe.gob.pe",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
}

# codigo_distrito -> nombre  (mismo orden que ONPE)
DISTRITOS = {
    1: "AMAZONAS", 2: "ANCASH", 3: "APURIMAC", 4: "AREQUIPA",
    5: "AYACUCHO", 6: "CAJAMARCA", 7: "CALLAO", 8: "CUSCO",
    9: "HUANCAVELICA", 10: "HUANUCO", 11: "ICA", 12: "JUNIN",
    13: "LA LIBERTAD", 14: "LAMBAYEQUE", 15: "LIMA METROPOLITANA",
    16: "LIMA PROVINCIAS", 17: "LORETO", 18: "MADRE DE DIOS",
    19: "MOQUEGUA", 20: "PASCO", 21: "PIURA", 22: "PUNO",
    23: "SAN MARTIN", 24: "TACNA", 25: "TUMBES", 26: "UCAYALI",
}


async def _get(client: httpx.AsyncClient, url: str) -> dict:
    try:
        r = await client.get(url, headers=API_HDR, timeout=15.0)
        if "json" not in r.headers.get("content-type", ""):
            return {}
        return r.json()
    except Exception as e:
        log.warning("GET error %s: %s", url[-80:], e)
        return {}


async def fetch_fresh() -> bool:
    """
    Descarga datos frescos de ONPE y actualiza los JSON en data/.
    Devuelve True si al menos los datos presidenciales se actualizaron.
    """
    log.info("Iniciando refresco de datos ONPE...")
    ok = False

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Iniciar sesión visitando la SPA y la página de resumen
        try:
            await client.get(SPA, headers=BROWSER_HDR, timeout=15.0)
            await client.get(RESUMEN, headers=BROWSER_HDR, timeout=15.0)
        except Exception:
            pass

        # ── 1. Presidencial nacional + mapa-calor ──────────────────────────
        pres_part = await _get(client,
            f"{BASE}/eleccion-presidencial/participantes-ubicacion-geografica-nombre"
            f"?idEleccion=10&tipoFiltro=eleccion")
        pres_tot = await _get(client,
            f"{BASE}/resumen-general/totales?idEleccion=10&tipoFiltro=eleccion")
        mapa_calor = await _get(client,
            f"{BASE}/resumen-general/mapa-calor"
            f"?idAmbitoGeografico=1&idEleccion=10&tipoFiltro=ambito_geografico")

        if pres_part.get("success"):
            # Actualizar presidencial_full.json
            pf_path = DATA_DIR / "presidencial_full.json"
            existing = {}
            if pf_path.exists():
                existing = json.loads(pf_path.read_text(encoding="utf-8"))

            part_url = (f"{BASE}/eleccion-presidencial/participantes-ubicacion-geografica-nombre"
                        f"?idEleccion=10&tipoFiltro=eleccion")
            tot_url  = f"{BASE}/resumen-general/totales?idEleccion=10&tipoFiltro=eleccion"
            existing[part_url] = pres_part
            if pres_tot.get("success"):
                existing[tot_url] = pres_tot
            pf_path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
            log.info("Presidencial: %d candidatos", len(pres_part.get("data", [])))
            ok = True

        if mapa_calor.get("success"):
            # Actualizar navigation_capture.json
            nc_path = DATA_DIR / "navigation_capture.json"
            nc = {}
            if nc_path.exists():
                nc = json.loads(nc_path.read_text(encoding="utf-8"))
            mc_url = (f"{BASE}/resumen-general/mapa-calor"
                      f"?idAmbitoGeografico=1&idEleccion=10&tipoFiltro=ambito_geografico")
            nc.setdefault("presidencial_navigation", {})[mc_url] = mapa_calor
            nc_path.write_text(json.dumps(nc, ensure_ascii=False), encoding="utf-8")
            log.info("Mapa-calor: %d departamentos", len(mapa_calor.get("data", [])))

        # ── 2. Presidencial por departamento ──────────────────────────────
        # Endpoint descubierto: GET con tipoFiltro=ubigeo_nivel_01 + idUbigeoDepartamento
        UBIGEO_NOMBRE_PRES = {
            10000: "AMAZONAS",    20000: "ANCASH",       30000: "APURIMAC",
            40000: "AREQUIPA",    50000: "AYACUCHO",     60000: "CAJAMARCA",
            70000: "CUSCO",       80000: "HUANCAVELICA", 90000: "HUANUCO",
            100000: "ICA",        110000: "JUNIN",       120000: "LA LIBERTAD",
            130000: "LAMBAYEQUE", 140000: "LIMA",        150000: "LORETO",
            160000: "MADRE DE DIOS", 170000: "MOQUEGUA", 180000: "PASCO",
            190000: "PIURA",      200000: "PUNO",        210000: "SAN MARTIN",
            220000: "TACNA",      230000: "TUMBES",      240000: "UCAYALI",
            250000: "CALLAO",
        }
        pres_dep = {}
        for ubigeo, nombre in UBIGEO_NOMBRE_PRES.items():
            pp = await _get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idAmbitoGeografico=1&idEleccion=10&tipoFiltro=ubigeo_nivel_01&idUbigeoDepartamento={ubigeo}")
            pt = await _get(client,
                f"{BASE}/resumen-general/totales"
                f"?idAmbitoGeografico=1&idEleccion=10&tipoFiltro=ubigeo_nivel_01&idUbigeoDepartamento={ubigeo}")
            if pp.get("success") and pp.get("data"):
                pres_dep[nombre] = {
                    "participantes": pp["data"],
                    "totales": pt.get("data", {}),
                }

        if pres_dep:
            (DATA_DIR / "presidencial_departamentos.json").write_text(
                json.dumps(pres_dep, ensure_ascii=False), encoding="utf-8")
            log.info("Presidencial por departamento: %d departamentos", len(pres_dep))

        # ── 2b. Composición de votos certificados por JEE (estadoActa=JEE) ──
        jee_dep = {}
        for ubigeo, nombre in UBIGEO_NOMBRE_PRES.items():
            jee_p = await _get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idAmbitoGeografico=1&idEleccion=10&tipoFiltro=ubigeo_nivel_01"
                f"&idUbigeoDepartamento={ubigeo}&estadoActa=JEE")
            if jee_p.get("success") and jee_p.get("data"):
                jee_dep[nombre] = jee_p["data"]

        if jee_dep:
            (DATA_DIR / "presidencial_jee_dep.json").write_text(
                json.dumps(jee_dep, ensure_ascii=False), encoding="utf-8")
            log.info("JEE por departamento: %d departamentos", len(jee_dep))

        # ── 2c. Votos SOLO actas ONPE contabilizadas (excluyendo JEE) ────────
        contab_dep = {}
        for ubigeo, nombre in UBIGEO_NOMBRE_PRES.items():
            cp = await _get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idAmbitoGeografico=1&idEleccion=10&tipoFiltro=ubigeo_nivel_01"
                f"&idUbigeoDepartamento={ubigeo}&estadoActa=CONTABILIZADA")
            if cp.get("success") and cp.get("data"):
                contab_dep[nombre] = cp["data"]

        if contab_dep:
            (DATA_DIR / "presidencial_contab_dep.json").write_text(
                json.dumps(contab_dep, ensure_ascii=False), encoding="utf-8")
            log.info("Contabilizadas por departamento: %d departamentos", len(contab_dep))

        # ── 3. Senado regional + Diputados por distrito (httpx) ────────────
        senado_reg = {}
        diputados  = {}

        for cod, nombre in DISTRITOS.items():
            # Senado regional (idEleccion=14)
            sr_p = await _get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idEleccion=14&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")
            sr_t = await _get(client,
                f"{BASE}/resumen-general/totales"
                f"?idEleccion=14&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")

            if sr_p.get("success") and sr_p.get("data"):
                senado_reg[nombre] = {
                    "participantes": sr_p["data"],
                    "totales": sr_t.get("data", {}),
                }

            # Diputados (idEleccion=13)
            dp_p = await _get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idEleccion=13&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")
            dp_t = await _get(client,
                f"{BASE}/resumen-general/totales"
                f"?idEleccion=13&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")

            if dp_p.get("success") and dp_p.get("data"):
                diputados[nombre] = {
                    "participantes": dp_p["data"],
                    "totales": dp_t.get("data", {}),
                }

        if senado_reg:
            (DATA_DIR / "senado_regional_distritos.json").write_text(
                json.dumps(senado_reg, ensure_ascii=False), encoding="utf-8")
            log.info("Senado regional: %d distritos", len(senado_reg))

        if diputados:
            (DATA_DIR / "diputados_distritos.json").write_text(
                json.dumps(diputados, ensure_ascii=False), encoding="utf-8")
            log.info("Diputados: %d distritos", len(diputados))

    log.info("Refresco completado: %s", datetime.now().strftime("%H:%M:%S"))
    return ok


async def loop(interval_seconds: int, refresh_fn):
    """
    Llama refresh_fn() cada interval_seconds.
    refresh_fn puede ser sync o async; si es async, se awaita.
    """
    import inspect
    first = True
    while True:
        if not first:
            await asyncio.sleep(interval_seconds)
        first = False
        try:
            result = refresh_fn()
            if inspect.isawaitable(result):
                ok = await result
            else:
                ok = result
            log.info("Refresco completado (ok=%s): %s", ok, datetime.now().strftime("%H:%M:%S"))
        except Exception as e:
            log.error("Error en refresco: %s", e)
