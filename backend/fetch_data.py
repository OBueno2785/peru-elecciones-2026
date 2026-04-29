"""
Fetcher directo de la API de ONPE 2026.
Usa los endpoints descubiertos para obtener todos los datos.
"""
import sys
import json
import time
from pathlib import Path
import httpx

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend"
SPA  = "https://resultadoelectoral.onpe.gob.pe/"

ELECCIONES = {
    "presidencial":    10,
    "senado_nacional": 15,
    "senado_regional": 14,
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://resultadoelectoral.onpe.gob.pe/main/resumen",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def get(client: httpx.Client, url: str) -> dict:
    try:
        r = client.get(url, headers=API_HEADERS, timeout=15.0)
        ct = r.headers.get("content-type", "")
        if "json" not in ct:
            return {}
        return r.json()
    except Exception as e:
        print(f"  ERROR {url[-80:]}: {e}")
        return {}


def fetch_all():
    result = {}

    with httpx.Client(follow_redirects=True) as client:
        # Inicializar sesion visitando la SPA
        print("[init] Cargando SPA para iniciar sesion...")
        client.get(SPA, headers=BROWSER_HEADERS)

        # 1. Metadatos
        print("[1/4] Metadatos...")
        proceso = get(client, f"{BASE}/proceso/proceso-electoral-activo")
        distritos_r = get(client, f"{BASE}/distrito-electoral/distritos")
        elecciones_r = get(client, f"{BASE}/proceso/2/elecciones")

        distritos = distritos_r.get("data", [])
        distritos_peru = [d for d in distritos if d["codigo"] <= 26]

        result["meta"] = {
            "proceso": proceso.get("data", {}),
            "distritos": distritos,
            "elecciones": elecciones_r.get("data", []),
        }
        print(f"  Proceso: {result['meta']['proceso'].get('nombre', '?')}")
        print(f"  Distritos: {len(distritos)}")

        # 2. Datos nacionales
        print("\n[2/4] Datos nacionales...")
        result["nacional"] = {}
        for tipo, id_elec in ELECCIONES.items():
            print(f"  {tipo} (id={id_elec})")
            p = get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idEleccion={id_elec}&tipoFiltro=eleccion")
            t = get(client,
                f"{BASE}/resumen-general/totales"
                f"?idEleccion={id_elec}&tipoFiltro=eleccion")
            result["nacional"][tipo] = {
                "participantes": p.get("data", []),
                "totales": t.get("data", {}),
            }
            n = len(result["nacional"][tipo]["participantes"])
            pct = result["nacional"][tipo]["totales"].get("actasContabilizadas", "?")
            print(f"    {n} candidatos, {pct}% actas procesadas")

        # 3. Datos por distrito - presidencial
        print("\n[3/4] Datos por departamento (presidencial)...")
        result["distritos"] = {}

        for d in distritos_peru:
            cod = d["codigo"]
            nombre = d["nombre"]
            print(f"  [{cod:2d}] {nombre}")

            p = get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idAmbitoGeografico=1&idEleccion=10"
                f"&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")
            t = get(client,
                f"{BASE}/resumen-general/totales"
                f"?idAmbitoGeografico=1&idEleccion=10"
                f"&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")

            result["distritos"][cod] = {
                "nombre": nombre,
                "presidencial": {
                    "participantes": p.get("data", []),
                    "totales": t.get("data", {}),
                },
            }
            np = len(result["distritos"][cod]["presidencial"]["participantes"])
            print(f"    {np} candidatos")

        # 4. Datos por distrito - senado nacional
        print("\n[4/4] Datos por departamento (senado nacional)...")
        for d in distritos_peru:
            cod = d["codigo"]
            nombre = d["nombre"]
            print(f"  [{cod:2d}] {nombre}")

            p = get(client,
                f"{BASE}/resumen-general/participantes"
                f"?idAmbitoGeografico=1&idEleccion=15"
                f"&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")
            t = get(client,
                f"{BASE}/resumen-general/totales"
                f"?idAmbitoGeografico=1&idEleccion=15"
                f"&tipoFiltro=distrito_electoral&idDistritoElectoral={cod}")

            result["distritos"][cod]["senado_nacional"] = {
                "participantes": p.get("data", []),
                "totales": t.get("data", {}),
            }
            ns = len(result["distritos"][cod]["senado_nacional"]["participantes"])
            print(f"    {ns} candidatos")

    # Guardar
    out = DATA_DIR / "onpe_data.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {out}")
    print(f"Distritos con datos: {len(result['distritos'])}")
    return result


if __name__ == "__main__":
    fetch_all()
