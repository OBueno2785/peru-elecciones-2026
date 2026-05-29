"""
Backend FastAPI - Elecciones Peru 2026
Sirve datos procesados de ONPE.
"""
import asyncio
import json
import logging
import threading
import time
import unicodedata
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import refresher
from refresher import UBIGEO_NOMBRE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

DATA_DIR = Path(__file__).resolve().parent / "data"
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

_cache: Optional[dict] = None
REFRESH_INTERVAL = 5 * 60  # 5 minutos
_refresh_lock = asyncio.Lock()      # serializa descargas de ONPE (async)
_cache_lock = threading.Lock()      # serializa build_cache() entre peticiones sync
# Cooldown del refresco manual público (anti-amplificación)
REFRESH_COOLDOWN = 30
_last_refresh_ts = 0.0


def _invalidate():
    """Descarta el cache; la próxima petición lo reconstruirá."""
    global _cache
    _cache = None


async def _fetch_and_invalidate():
    """Descarga datos frescos de ONPE y descarta el cache de forma atómica."""
    async with _refresh_lock:
        ok = await refresher.fetch_fresh()
        if ok:
            _invalidate()
    return ok


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arrancar loop de refresco en segundo plano
    task = asyncio.create_task(refresher.loop(REFRESH_INTERVAL, _fetch_and_invalidate))
    yield
    task.cancel()


app = FastAPI(title="Elecciones Peru 2026 API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"],
)

# Colores fijos por partido (hex)
COLORES_PARTIDO = {
    "FUERZA POPULAR":              "#F97316",
    "RENOVACION POPULAR":          "#1D3557",
    "PARTIDO DEL BUEN GOBIERNO":   "#457B9D",
    "JUNTOS POR EL PERU":          "#E63946",
    "ALIANZA PARA EL PROGRESO":    "#2A9D8F",
    "UNION POR EL PERU":           "#E9C46A",
    "PODEMOS PERU":                "#264653",
    "PERU LIBRE":                  "#E76F51",
    "ACCION POPULAR":              "#A8DADC",
    "SOMOS PERU":                  "#F1FAEE",
    "PARTIDO MORADO":              "#9B5DE5",
    "ALIANZA ELECTORAL VENCEREMOS":"#43AA8B",
    "PARTIDO CIVICO OBRAS":        "#90BE6D",
    "PERU BICENTENARIO":           "#577590",
    "PARTIDO HUMANISTA":           "#F9C74F",
    "AVANCEMOS":                   "#F8961E",
    "SALVEMOS AL PERU":            "#43A6C6",
    "DEFAULT":                     "#888888",
}


def norm(s: str) -> str:
    """Normaliza un string: sin tildes, mayusculas, limpio."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()


_COLORES_NORM = {norm(k): v for k, v in COLORES_PARTIDO.items() if k != "DEFAULT"}
# Claves ordenadas por longitud desc: ante varias coincidencias gana la más específica
_COLORES_KEYS = sorted(_COLORES_NORM, key=len, reverse=True)


def color_for(partido: str) -> str:
    p = norm(partido)
    if p in _COLORES_NORM:
        return _COLORES_NORM[p]
    # Match en una sola dirección (clave contenida en el nombre), nunca al revés:
    # evita que un nombre corto coincida con cualquier clave que lo contenga.
    for k in _COLORES_KEYS:
        if k in p:
            return _COLORES_NORM[k]
    return COLORES_PARTIDO["DEFAULT"]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # Un JSON corrupto (p. ej. escritura interrumpida) no debe tumbar la API
        logging.getLogger(__name__).warning("load_json fallo en %s: %s", path, e)
        return {}


def top_candidatos(lista: list, n: int = 10) -> list:
    """Retorna los top N candidatos ordenados por % de votos validos."""
    if not lista:
        return []
    sorted_list = sorted(
        lista,
        key=lambda x: float(x.get("porcentajeVotosValidos", 0)),
        reverse=True,
    )
    result = []
    for c in sorted_list[:n]:
        partido = c.get("nombreAgrupacionPolitica", "")
        result.append({
            "partido": partido,
            "candidato": c.get("nombreCandidato", ""),
            "votos": int(c.get("totalVotosValidos", 0)),
            "pct": float(c.get("porcentajeVotosValidos", 0)),
            "pctEmitidos": float(c.get("porcentajeVotosEmitidos", 0)),
            "color": color_for(partido),
        })
    return result


def build_cache() -> dict:
    """Construye el cache de datos procesados."""
    # Nacional presidencial
    presidencial_full = load_json(DATA_DIR / "presidencial_full.json")
    pres_url = next(
        (u for u in presidencial_full if "participantes-ubicacion-geografica-nombre" in u),
        None,
    )
    pres_nacional = []
    if pres_url:
        pres_nacional = top_candidatos(
            presidencial_full[pres_url].get("data", []), n=38
        )

    # Totales presidencial
    pres_totales_url = next(
        (u for u in presidencial_full if "totales" in u and "idEleccion=10" in u),
        None,
    )
    pres_totales = {}
    if pres_totales_url:
        pres_totales = presidencial_full[pres_totales_url].get("data", {})

    # Mapa-calor presidencial por departamento (desde navigation_capture)
    mapa_calor_data = {}
    nav_capture = load_json(DATA_DIR / "navigation_capture.json")
    for url, body in nav_capture.get("presidencial_navigation", {}).items():
        if "mapa-calor" in url and "idAmbitoGeografico=1" in url:
            for item in body.get("data", []):
                ubigeo = item.get("ubigeoNivel01")
                if ubigeo:
                    mapa_calor_data[ubigeo] = item
    # Fallback: buscar en presidencial_full
    if not mapa_calor_data:
        for url, body in presidencial_full.items():
            if "mapa-calor" in url and "idAmbitoGeografico=1" in url:
                for item in body.get("data", []):
                    ubigeo = item.get("ubigeoNivel01")
                    if ubigeo:
                        mapa_calor_data[ubigeo] = item

    # Senado regional por distrito
    senado_reg = load_json(DATA_DIR / "senado_regional_distritos.json")

    # Diputados por distrito
    diputados = load_json(DATA_DIR / "diputados_distritos.json")

    # Nacional - raw capture
    raw = load_json(DATA_DIR / "raw_capture.json")
    senado_nac_url = next(
        (u for u in raw if "idEleccion=15" in u and "tipoFiltro=eleccion" in u
         and "participantes" in u), None
    )
    senado_nac_nacional = []
    senado_nac_totales = {}
    if senado_nac_url:
        senado_nac_nacional = top_candidatos(raw[senado_nac_url].get("data", []), n=38)
    senado_nac_tot_url = next(
        (u for u in raw if "idEleccion=15" in u and "tipoFiltro=eleccion" in u
         and "totales" in u), None
    )
    if senado_nac_tot_url:
        senado_nac_totales = raw[senado_nac_tot_url].get("data", {})

    # Construir mapa por departamento
    # Mapping nombre ONPE -> departamento normalizado
    def build_mapa_distrito(datos_por_nombre: dict) -> dict:
        result = {}
        for nombre, data in datos_por_nombre.items():
            nombre_norm = norm(nombre)
            cands = top_candidatos(data.get("participantes", []), n=10)
            totales = data.get("totales", {})
            if not cands:
                continue
            total_actas_n = int(totales.get("totalActas", 0) or 0)
            total_votos = int(totales.get("totalVotosValidos", 0) or 0)
            pct_actas_raw = totales.get("actasContabilizadas")
            # None cuando ONPE no devolvió totales o aún no hay votos contados
            sin_datos = (pct_actas_raw is None or total_actas_n == 0 or total_votos == 0)
            pct_actas = None if sin_datos else float(pct_actas_raw)
            # Lider None si no hay votos: el mapa muestra gris en vez de color arbitrario
            lider = cands[0] if not sin_datos else None
            result[nombre_norm] = {
                "nombre": nombre,
                "lider": lider,
                "top": cands,           # siempre mostrar candidatos en el panel
                "actasContabilizadas": pct_actas,
                "totalActas": total_actas_n,
                "contabilizadas": int(totales.get("contabilizadas", 0) or 0),
                "totalVotosValidos": total_votos,
            }
        return result

    mapa_senado_reg = build_mapa_distrito(senado_reg)
    mapa_diputados = build_mapa_distrito(diputados)

    def aggregate_nacional(datos_por_nombre: dict) -> dict:
        """Agrega totales nacionales sumando votos por partido en todos los distritos."""
        EXCLUIR = {"VOTOS NULOS", "VOTOS EN BLANCO", "VOTOS IMPUGNADOS"}
        party_votes: dict = defaultdict(int)
        total_actas = 0
        contabilizadas = 0
        for nombre, data in datos_por_nombre.items():
            totales = data.get("totales", {})
            total_actas += int(totales.get("totalActas", 0))
            contabilizadas += int(totales.get("contabilizadas", 0))
            for p in data.get("participantes", []):
                partido = p.get("nombreAgrupacionPolitica", "")
                if partido.upper() in EXCLUIR:
                    continue
                votes = int(p.get("totalVotosValidos", 0))
                party_votes[partido] += votes
        total_validos = sum(party_votes.values()) or 1
        top = sorted(
            [
                {
                    "partido": partido,
                    "votos": votos,
                    "pct": round(votos / total_validos * 100, 2),
                    "color": color_for(partido),
                }
                for partido, votos in party_votes.items()
            ],
            key=lambda x: -x["votos"],
        )[:38]
        actas_pct = round(contabilizadas / total_actas * 100, 2) if total_actas else 0
        return {
            "top": top,
            "totales": {
                "actasContabilizadas": actas_pct,
                "totalActas": total_actas,
                "contabilizadas": contabilizadas,
            },
        }

    senado_reg_nacional = aggregate_nacional(senado_reg)
    diputados_nacional = aggregate_nacional(diputados)

    # Presidencial por departamento
    pres_dep_raw = load_json(DATA_DIR / "presidencial_departamentos.json")
    mapa_pres_dep = build_mapa_distrito(pres_dep_raw) if pres_dep_raw else {}

    # Para presidencial: combinar mapa-calor (progreso de conteo) con datos por
    # departamento. UBIGEO_NOMBRE se importa de refresher (fuente única).
    mapa_pres = {}
    for ubigeo, item in mapa_calor_data.items():
        nombre = UBIGEO_NOMBRE.get(ubigeo, str(ubigeo))
        nombre_norm = norm(nombre)
        dep_data = mapa_pres_dep.get(nombre_norm, {})
        # Use per-department candidates if available, otherwise fall back to national
        dep_top = dep_data.get("top") or pres_nacional[:10]
        dep_lider = dep_data.get("lider") or (pres_nacional[0] if pres_nacional else None)
        mapa_pres[nombre_norm] = {
            "nombre": nombre,
            "actasContabilizadas": float(item.get("porcentajeActasContabilizadas", 0)),
            "actasContabilizadasN": int(item.get("actasContabilizadas", 0)),
            "lider": dep_lider,
            "top": dep_top,
            "totalActas": dep_data.get("totalActas", 0),
            "contabilizadas": dep_data.get("contabilizadas", 0),
            "totalVotosValidos": dep_data.get("totalVotosValidos", 0),
        }

    return {
        "presidencial": {
            "nacional": {
                "top": pres_nacional,
                "totales": {
                    # Tres estados ONPE mutuamente excluyentes — NO sumar
                    "actasContabilizadas": round(float(pres_totales.get("actasContabilizadas", 0)), 3),
                    "actasEnviadasJee":    round(float(pres_totales.get("actasEnviadasJee", 0)), 3),
                    "actasPendientes":     round(float(pres_totales.get("actasPendientesJee", 0)), 3),
                    "totalActas":          int(pres_totales.get("totalActas", 0)),
                    "contabilizadas":      int(pres_totales.get("contabilizadas", 0)),
                    "enviadasJee":         int(pres_totales.get("enviadasJee", 0)),
                    "totalVotosValidos":   int(pres_totales.get("totalVotosValidos", 0)),
                    "totalVotosEmitidos":  int(pres_totales.get("totalVotosEmitidos", 0)),
                },
            },
            "mapa": mapa_pres,
            "nota": "Presidencial es eleccion nacional. El mapa muestra avance de conteo por departamento.",
        },
        "senado_nacional": {
            "nacional": {
                "top": senado_nac_nacional,
                "totales": {
                    "actasContabilizadas": float(senado_nac_totales.get("actasContabilizadas", 0)),
                    "totalActas": int(senado_nac_totales.get("totalActas", 0)),
                    "contabilizadas": int(senado_nac_totales.get("contabilizadas", 0)),
                },
            },
            "mapa": mapa_pres,  # Reusar mapa-calor presidencial para progreso
        },
        "senado_regional": {
            "nacional": senado_reg_nacional,
            "mapa": mapa_senado_reg,
        },
        "diputados": {
            "nacional": diputados_nacional,
            "mapa": mapa_diputados,
        },
    }


HISTORIAL_PATH = DATA_DIR / "historial.json"
_historial: list = []

# Puntos históricos fijos capturados el día de la elección (13-abr-2026)
# Se insertan automáticamente si no están en el historial guardado
_SEED_HISTORIAL = [
    {
        "ts": "2026-04-13T16:47:01Z",
        "actas": 54.5,
        "candidatos": [
            {"partido": "FUERZA POPULAR",            "pct": 16.957, "color": "#F97316"},
            {"partido": "RENOVACIÓN POPULAR",        "pct": 14.429, "color": "#1D3557"},
            {"partido": "PARTIDO DEL BUEN GOBIERNO", "pct": 12.749, "color": "#457B9D"},
            {"partido": "PARTIDO CÍVICO OBRAS",      "pct":  9.870, "color": "#90BE6D"},
            {"partido": "PARTIDO PAÍS PARA TODOS",   "pct":  8.437, "color": "#888888"},
            {"partido": "JUNTOS POR EL PERÚ",        "pct":  8.092, "color": "#E63946"},
            {"partido": "AHORA NACIÓN - AN",         "pct":  7.588, "color": "#888888"},
            {"partido": "ALIANZA PARA EL PROGRESO",  "pct":  3.773, "color": "#2A9D8F"},
        ],
    },
]


def _load_historial():
    global _historial
    loaded = []
    if HISTORIAL_PATH.exists():
        try:
            loaded = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            loaded = []
    # Garantizar que los puntos seed siempre estén presentes
    ts_existentes = {s["ts"] for s in loaded}
    extras = [s for s in _SEED_HISTORIAL if s["ts"] not in ts_existentes]
    _historial = sorted(extras + loaded, key=lambda x: x["ts"])
    # Si se añadieron seeds, persistir
    if extras:
        HISTORIAL_PATH.write_text(json.dumps(_historial, ensure_ascii=False), encoding="utf-8")


def _append_historial(data: dict):
    """Guarda un snapshot solo cuando ONPE publicó datos nuevos (cambio real en votos)."""
    top = data["presidencial"]["nacional"]["top"]
    actas = data["presidencial"]["nacional"]["totales"].get("actasContabilizadas", 0)
    if not top:
        return

    candidatos = [
        {"partido": c["partido"], "pct": round(c["pct"], 3), "color": c["color"]}
        for c in top[:8]
    ]
    snapshot = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actas": round(actas, 2),
        "candidatos": candidatos,
    }

    # Detectar si ONPE actualizó: candidatos cambiaron O avanzaron las actas
    if _historial:
        prev = _historial[-1]
        prev_pcts = {c["partido"]: c["pct"] for c in prev["candidatos"]}
        new_pcts  = {c["partido"]: c["pct"] for c in candidatos}
        candidatos_cambiaron = any(
            abs(new_pcts.get(p, 0) - prev_pcts.get(p, 0)) >= 0.005
            for p in new_pcts
        )
        # Umbral dinámico: más sensible en la recta final del conteo
        umbral_actas = 0.1 if actas >= 90 else 0.3 if actas >= 75 else 0.5
        actas_avanzaron = abs(round(actas, 2) - prev["actas"]) >= umbral_actas
        if not candidatos_cambiaron and not actas_avanzaron:
            return

    _historial.append(snapshot)
    # Conservar máximo 500 puntos (~1.7 días a 5 min)
    if len(_historial) > 500:
        _historial.pop(0)
    HISTORIAL_PATH.write_text(json.dumps(_historial, ensure_ascii=False), encoding="utf-8")
    logging.getLogger("historial").info(
        "Snapshot #%d guardado: actas=%.2f%% ts=%s", len(_historial), actas, snapshot["ts"]
    )


def get_data() -> dict:
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                data = build_cache()
                _append_historial(data)
                _cache = data
    return _cache


_load_historial()


# ── Endpoints ──────────────────────────────────────────

@app.get("/api/status")
def status():
    data = get_data()
    return {
        "ok": True,
        "presidencial_mapa": len(data["presidencial"]["mapa"]),
        "senado_reg_mapa": len(data["senado_regional"]["mapa"]),
        "diputados_mapa": len(data["diputados"]["mapa"]),
        "pres_candidatos": len(data["presidencial"]["nacional"]["top"]),
    }


@app.get("/api/presidencial")
def presidencial():
    return get_data()["presidencial"]


@app.get("/api/senado-nacional")
def senado_nacional():
    return get_data()["senado_nacional"]


@app.get("/api/senado-regional")
def senado_regional():
    return get_data()["senado_regional"]


@app.get("/api/diputados")
def diputados():
    return get_data()["diputados"]


@app.get("/api/mapa/{tipo}")
def mapa(tipo: str):
    """
    Retorna datos del mapa para un tipo de eleccion.
    tipo: presidencial | senado-regional | diputados
    """
    data = get_data()
    tipo_map = {
        "presidencial": data["presidencial"]["mapa"],
        "senado-regional": data["senado_regional"]["mapa"],
        "diputados": data["diputados"]["mapa"],
    }
    if tipo not in tipo_map:
        raise HTTPException(400, f"Tipo invalido. Opciones: {list(tipo_map)}")
    return {"mapa": tipo_map[tipo]}


@app.get("/api/historial")
def historial():
    return {"snapshots": _historial}


@app.get("/api/composicion-jee")
def composicion_jee():
    """
    Composición real del voto en actas certificadas por el JEE, por departamento.
    Datos frescos del endpoint estadoActa=JEE de ONPE.
    """
    EXCLUIR = {"VOTOS NULOS", "VOTOS EN BLANCO", "VOTOS IMPUGNADOS"}
    jee_dep  = load_json(DATA_DIR / "presidencial_jee_dep.json")
    pres_dep = load_json(DATA_DIR / "presidencial_departamentos.json")

    if not jee_dep:
        raise HTTPException(503, "Datos JEE no disponibles aún. Ejecuta /api/refresh.")

    # ── Acumular totales nacionales desde JEE ─────────────────────────────
    nac_votos: dict = defaultdict(int)
    nac_total = 0
    for nombre, cands in jee_dep.items():
        for c in cands:
            partido = c.get("nombreAgrupacionPolitica", "")
            if partido.upper() in EXCLUIR:
                continue
            votos = int(c.get("totalVotosValidos", 0))
            nac_votos[partido] += votos
            nac_total += votos

    # Top partidos nacionales (para el orden de columnas en el frontend)
    top_partidos_nac = sorted(nac_votos.items(), key=lambda x: -x[1])
    pct_nac = {p: round(v / nac_total * 100, 2) for p, v in top_partidos_nac}
    top_nac = [
        {"partido": p, "votos": v, "pct": pct_nac[p], "color": color_for(p)}
        for p, v in top_partidos_nac[:10]
    ]

    # ── Por departamento ──────────────────────────────────────────────────
    departamentos = []
    for nombre, cands in sorted(jee_dep.items()):
        cands_validos = [c for c in cands if c.get("nombreAgrupacionPolitica", "").upper() not in EXCLUIR]
        total_dep = sum(int(c.get("totalVotosValidos", 0)) for c in cands_validos)
        if not total_dep:
            continue

        top_dep = sorted(cands_validos, key=lambda x: int(x.get("totalVotosValidos", 0)), reverse=True)

        candidatos = []
        for c in top_dep[:10]:
            partido  = c.get("nombreAgrupacionPolitica", "")
            candidato = c.get("nombreCandidato", "")
            votos    = int(c.get("totalVotosValidos", 0))
            pct_dep  = round(votos / total_dep * 100, 2)
            pct_nacional = pct_nac.get(partido, 0)
            candidatos.append({
                "partido":   partido,
                "candidato": candidato,
                "votos":     votos,
                "pct":       pct_dep,
                "color":     color_for(partido),
                "desv_nac":  round(pct_dep - pct_nacional, 2),  # + = sobre la media nacional
            })

        # Totales del departamento (actas)
        t = pres_dep.get(nombre, {}).get("totales", {})
        margen = round(candidatos[0]["pct"] - candidatos[1]["pct"], 2) if len(candidatos) >= 2 else None

        departamentos.append({
            "nombre":          nombre,
            "total_validos":   total_dep,
            "candidatos":      candidatos,
            "lider":           candidatos[0] if candidatos else None,
            "margen_1_vs_2":   margen,
            "actas_contabilizadas": round(float(t.get("actasContabilizadas", 0)), 2),
            "actas_enviadas_jee":   round(float(t.get("actasEnviadasJee", 0)), 2),
            "actas_pendientes_jee": round(float(t.get("actasPendientesJee", 0)), 2),
            "n_pendientes":         int(t.get("pendientesJee", 0)),
            "votos_estimados_pendientes": int(
                (total_dep / max(1, int(t.get("contabilizadas", 0)) + int(t.get("enviadasJee", 0))))
                * int(t.get("pendientesJee", 0))
            ),
        })

    # Ordenar por votos totales desc (peso electoral)
    departamentos.sort(key=lambda d: -d["total_validos"])

    return {
        "nacional": {
            "total_validos": nac_total,
            "top": top_nac,
        },
        "departamentos": departamentos,
    }


@app.get("/api/analisis-jee")
def analisis_jee():
    """
    Análisis detallado del estado de actas: contabilizadas / enviadas al JEE / pendientes.
    Los tres estados son mutuamente excluyentes y suman el total de actas.
    """
    pres_full  = load_json(DATA_DIR / "presidencial_full.json")
    pres_dep   = load_json(DATA_DIR / "presidencial_departamentos.json")

    # ── Totales nacionales ───────────────────────────────────────────────
    tot_url = next((u for u in pres_full if "totales" in u and "idEleccion=10" in u), None)
    nat = pres_full[tot_url]["data"] if tot_url else {}

    total_actas       = int(nat.get("totalActas", 0))
    n_contab          = int(nat.get("contabilizadas", 0))
    n_jee             = int(nat.get("enviadasJee", 0))
    n_pend            = int(nat.get("pendientesJee", 0))
    n_sin_procesar    = max(0, total_actas - n_contab - n_jee - n_pend)
    total_emitidos    = int(nat.get("totalVotosEmitidos", 0))
    total_validos     = int(nat.get("totalVotosValidos", 0))

    pct_contab = round(float(nat.get("actasContabilizadas", 0)), 3)
    pct_jee    = round(float(nat.get("actasEnviadasJee", 0)), 3)
    pct_pend   = round(float(nat.get("actasPendientesJee", 0)), 3)
    pct_sin    = round(max(0.0, 100.0 - pct_contab - pct_jee - pct_pend), 3)

    # Votos promedio por acta (de las ya contabilizadas)
    votos_por_acta = round(total_validos / (n_contab + n_jee), 1) if (n_contab + n_jee) > 0 else 0

    # Votos estimados en actas pendientes
    votos_estimados_pend = int(votos_por_acta * n_pend)
    votos_estimados_sin  = int(votos_por_acta * n_sin_procesar)

    nacional = {
        "total_actas":      total_actas,
        "contabilizadas":   {"n": n_contab, "pct": pct_contab},
        "enviadas_jee":     {"n": n_jee,    "pct": pct_jee},
        "pendientes_jee":   {"n": n_pend,   "pct": pct_pend},
        "sin_procesar":     {"n": n_sin_procesar, "pct": pct_sin},
        "total_validos_publicados": total_validos,
        "total_emitidos":   total_emitidos,
        "votos_por_acta_promedio": votos_por_acta,
        "votos_estimados_pendientes": votos_estimados_pend,
    }

    # ── Por departamento ──────────────────────────────────────────────────
    EXCLUIR_CANDIDATOS = {"VOTOS NULOS", "VOTOS EN BLANCO", "VOTOS IMPUGNADOS"}

    departamentos = []
    for nombre, data in sorted(pres_dep.items()):
        t = data.get("totales", {})
        ta   = int(t.get("totalActas", 0))
        tc   = int(t.get("contabilizadas", 0))
        tj   = int(t.get("enviadasJee", 0))
        tp   = int(t.get("pendientesJee", 0))
        tsin = max(0, ta - tc - tj - tp)
        tv   = int(t.get("totalVotosValidos", 0))
        vpc  = round(tv / (tc + tj), 1) if (tc + tj) > 0 else 0
        v_pend_est = int(vpc * tp)

        # Top 3 candidatos actuales en este departamento
        cands = sorted(
            [p for p in data.get("participantes", [])
             if p.get("nombreAgrupacionPolitica", "").upper() not in EXCLUIR_CANDIDATOS],
            key=lambda x: float(x.get("porcentajeVotosValidos", 0)),
            reverse=True,
        )[:3]
        top3 = [
            {
                "partido":   c.get("nombreAgrupacionPolitica", ""),
                "candidato": c.get("nombreCandidato", ""),
                "pct":       round(float(c.get("porcentajeVotosValidos", 0)), 2),
                "votos":     int(c.get("totalVotosValidos", 0)),
                "color":     color_for(c.get("nombreAgrupacionPolitica", "")),
            }
            for c in cands
        ]

        # Margen entre 1° y 2°
        margen = round(top3[0]["pct"] - top3[1]["pct"], 2) if len(top3) >= 2 else None
        # Porcentaje de votos pendientes sobre total válidos actuales
        pct_impacto = round(v_pend_est / tv * 100, 1) if tv > 0 else 0

        departamentos.append({
            "nombre":            nombre,
            "total_actas":       ta,
            "contabilizadas":    {"n": tc, "pct": round(float(t.get("actasContabilizadas", 0)), 2)},
            "enviadas_jee":      {"n": tj, "pct": round(float(t.get("actasEnviadasJee", 0)), 2)},
            "pendientes_jee":    {"n": tp, "pct": round(float(t.get("actasPendientesJee", 0)), 2)},
            "sin_procesar":      {"n": tsin, "pct": round(tsin / ta * 100, 2) if ta else 0},
            "total_validos":     tv,
            "votos_por_acta":    vpc,
            "votos_estimados_pendientes": v_pend_est,
            "pct_impacto_pendientes": pct_impacto,
            "top3":              top3,
            "margen_1_vs_2":     margen,
        })

    # Ordenar por mayor % de pendientes + sin procesar (más incertidumbre primero)
    departamentos.sort(
        key=lambda d: d["pendientes_jee"]["pct"] + d["sin_procesar"]["pct"],
        reverse=True,
    )

    return {
        "nacional": nacional,
        "departamentos": departamentos,
        "nota": (
            "Contabilizadas: ONPE escrutó y publicó (incluidas en el conteo). "
            "Enviadas JEE: remitidas al Jurado Electoral Especial para certificación (también incluidas en el conteo). "
            "Pendientes JEE: en tránsito, AÚN NO incluidas en el conteo público. "
            "Sin procesar: no iniciadas."
        ),
    }


@app.get("/api/comparacion-actas")
def comparacion_actas():
    """
    Tres escenarios de conteo:
    1. Solo actas ONPE contabilizadas (92.96%) — usando estadoActa=CONTABILIZADA
    2. Procesadas completas (98.6%): contabilizadas + JEE — resultados actuales
    3. Proyección al 100%: si las pendientes siguen el mismo patrón
    Más: zona de incertidumbre y distribución geográfica de actas pendientes.
    Nota: ONPE expone la misma composición de votos para ambos filtros estadoActa;
    la diferencia se refleja en votos absolutos, no en porcentajes.
    """
    EXCLUIR = {"VOTOS NULOS", "VOTOS EN BLANCO", "VOTOS IMPUGNADOS"}

    # ── Totales ONPE ─────────────────────────────────────────────────────────
    pres_full = load_json(DATA_DIR / "presidencial_full.json")
    pres_url  = next((u for u in pres_full if "participantes-ubicacion-geografica-nombre" in u), None)
    tot_url   = next((u for u in pres_full if "totales" in u and "idEleccion=10" in u), None)

    all_cands = pres_full[pres_url]["data"] if pres_url else []
    nat       = pres_full[tot_url]["data"]  if tot_url  else {}

    n_contab    = int(nat.get("contabilizadas", 0))
    n_jee       = int(nat.get("enviadasJee", 0))
    n_pend      = int(nat.get("pendientesJee", 0))
    total_actas = int(nat.get("totalActas", 0))
    pct_contab  = round(float(nat.get("actasContabilizadas", 0)), 3)
    pct_jee     = round(float(nat.get("actasEnviadasJee", 0)), 3)
    pct_pend    = round(float(nat.get("actasPendientesJee", 0)), 3)
    total_validos = int(nat.get("totalVotosValidos", 0))

    # ── Votos por partido — estado actual (contabilizadas + JEE) ─────────────
    votos_actuales: dict = defaultdict(int)
    for c in all_cands:
        p = c.get("nombreAgrupacionPolitica", "")
        if p.upper() in EXCLUIR:
            continue
        votos_actuales[p] += int(c.get("totalVotosValidos", 0))
    total_actuales = sum(votos_actuales.values()) or 1

    def build_top_from_votos(votos_dict: dict, n: int = 8) -> list:
        total = sum(votos_dict.values()) or 1
        return sorted(
            [{"partido": p, "votos": v,
              "pct": round(v / total * 100, 3),
              "color": color_for(p)}
             for p, v in votos_dict.items() if v > 0],
            key=lambda x: -x["votos"],
        )[:n]

    top_actual = build_top_from_votos(votos_actuales)
    # Total de actas con votos publicados = contabilizadas + JEE (ambas incluidas en el dato ONPE)
    n_publicadas   = n_contab + n_jee
    pct_publicadas = round(pct_contab + pct_jee, 2)

    # ── Panel 1: Datos reales ONPE — solo contabilizadas ─────────────────────
    # votos_actuales = lo que ONPE publica = votos de las actas contabilizadas únicamente.
    # Las actas en JEE aún no tienen votos publicados (pendientes de certificación JEE).
    total_contab = total_actuales

    # ── Panel 2: Contabilizadas + estimación de votos JEE ────────────────────
    # Para cada departamento, estimamos los votos de las actas JEE:
    #   vpc_dep = tv_dep / tc_dep  (votos por acta contabilizada en ese departamento)
    #   v_jee_dep = vpc_dep × tj_dep
    # Distribuimos proporcionalmente según el perfil de voto actual del departamento.
    pres_dep_raw = load_json(DATA_DIR / "presidencial_departamentos.json")
    votos_jee_extra: dict = defaultdict(int)
    votos_jee_est = 0
    for nombre, dep_data in pres_dep_raw.items():
        t  = dep_data.get("totales", {})
        tc = int(t.get("contabilizadas", 0))
        tj = int(t.get("enviadasJee", 0))
        tv = int(t.get("totalVotosValidos", 0))
        if not tj or not tc:
            continue
        vpc_dep = tv / tc          # votos por acta contabilizada en este departamento
        v_jee_dep = round(vpc_dep * tj)
        votos_jee_est += v_jee_dep
        cands_dep = [
            c for c in dep_data.get("participantes", [])
            if c.get("nombreAgrupacionPolitica", "").upper() not in EXCLUIR
        ]
        total_dep_validos = sum(int(c.get("totalVotosValidos", 0)) for c in cands_dep) or 1
        for c in cands_dep:
            p = c.get("nombreAgrupacionPolitica", "")
            pct_dep = int(c.get("totalVotosValidos", 0)) / total_dep_validos
            votos_jee_extra[p] += round(pct_dep * v_jee_dep)

    todos_con_jee = set(votos_actuales.keys()) | set(votos_jee_extra.keys())
    votos_con_jee = {p: votos_actuales.get(p, 0) + votos_jee_extra.get(p, 0)
                     for p in todos_con_jee}
    total_con_jee = total_actuales + votos_jee_est

    # ── Panel 3: Panel 2 + estimación de votos pendientes ────────────────────
    votos_proyec_extra: dict = defaultdict(int)
    votos_pend_est = 0
    for nombre, dep_data in pres_dep_raw.items():
        t  = dep_data.get("totales", {})
        tc = int(t.get("contabilizadas", 0))
        tp = int(t.get("pendientesJee", 0))
        tv = int(t.get("totalVotosValidos", 0))
        if not tp or not tc:
            continue
        vpc_dep = tv / tc          # votos por acta contabilizada en este departamento
        v_pend_dep = round(vpc_dep * tp)
        votos_pend_est += v_pend_dep
        cands_dep = [
            c for c in dep_data.get("participantes", [])
            if c.get("nombreAgrupacionPolitica", "").upper() not in EXCLUIR
        ]
        total_dep_validos = sum(int(c.get("totalVotosValidos", 0)) for c in cands_dep) or 1
        for c in cands_dep:
            p = c.get("nombreAgrupacionPolitica", "")
            pct_dep = int(c.get("totalVotosValidos", 0)) / total_dep_validos
            votos_proyec_extra[p] += round(pct_dep * v_pend_dep)

    # Si no hay datos por departamento, usar promedio nacional como fallback
    if not votos_proyec_extra:
        vpa_nac = round(total_actuales / n_contab, 2) if n_contab else 0
        votos_pend_est = round(vpa_nac * n_pend)
        for p, v in votos_actuales.items():
            votos_proyec_extra[p] = round(v / total_actuales * votos_pend_est)

    todos_partidos = set(votos_con_jee.keys()) | set(votos_proyec_extra.keys())
    votos_proyec = {p: votos_con_jee.get(p, 0) + votos_proyec_extra.get(p, 0)
                    for p in todos_partidos}
    total_proyec = total_con_jee + votos_pend_est

    # ── Zona de incertidumbre (2° vs 3° y siguientes) ────────────────────────
    top8 = top_actual[:8]
    incertidumbre = []
    for i in range(1, min(6, len(top8))):
        c_actual  = top8[i]
        c_debajo  = top8[i + 1] if i + 1 < len(top8) else None
        diff_votos_arriba = round((top8[i-1]["pct"] - c_actual["pct"]) / 100 * total_actuales)
        diff_votos_abajo  = round((c_actual["pct"] - c_debajo["pct"]) / 100 * total_actuales) if c_debajo else None
        incertidumbre.append({
            "posicion":         i + 1,
            "partido":          c_actual["partido"],
            "color":            c_actual["color"],
            "pct":              c_actual["pct"],
            "votos":            c_actual["votos"],
            "votos_al_de_arriba":  diff_votos_arriba,
            "votos_sobre_el_de_abajo": diff_votos_abajo,
            "puede_subir":      diff_votos_arriba <= votos_pend_est,
            "puede_bajar":      diff_votos_abajo is not None and diff_votos_abajo <= votos_pend_est,
        })

    # ── Pendientes por departamento ───────────────────────────────────────────
    pres_dep = load_json(DATA_DIR / "presidencial_departamentos.json")
    pendientes_dep = []
    for nombre, data in sorted(pres_dep.items()):
        t  = data.get("totales", {})
        ta = int(t.get("totalActas", 0))
        tc = int(t.get("contabilizadas", 0))
        tj = int(t.get("enviadasJee", 0))
        tp = int(t.get("pendientesJee", 0))
        tv = int(t.get("totalVotosValidos", 0))
        if not ta or not tp:
            continue
        vpc = round(tv / (tc + tj), 1) if (tc + tj) > 0 else 0
        # Lider actual en este depto
        cands_dep = sorted(
            [p for p in data.get("participantes", [])
             if p.get("nombreAgrupacionPolitica", "").upper() not in EXCLUIR],
            key=lambda x: float(x.get("porcentajeVotosValidos", 0)), reverse=True
        )[:2]
        top2 = [{"partido": c.get("nombreAgrupacionPolitica",""),
                  "pct": round(float(c.get("porcentajeVotosValidos", 0)), 2),
                  "color": color_for(c.get("nombreAgrupacionPolitica",""))}
                 for c in cands_dep]
        pendientes_dep.append({
            "nombre":             nombre,
            "pendientes_n":       tp,
            "pendientes_pct":     round(float(t.get("actasPendientesJee", 0)), 2),
            "votos_estimados":    int(vpc * tp),
            "contabilizadas_pct": round(float(t.get("actasContabilizadas", 0)), 2),
            "jee_pct":            round(float(t.get("actasEnviadasJee", 0)), 2),
            "top2":               top2,
        })
    pendientes_dep.sort(key=lambda d: -d["pendientes_n"])

    return {
        "sin_jee": {
            "label":         f"Contabilizadas · {n_contab:,} actas",
            "descripcion":   f"Resultados reales publicados por ONPE: {n_contab:,} actas contabilizadas ({pct_contab:.2f}%). Son los datos oficiales actuales.",
            "actas_n":       n_contab,
            "actas_pct":     pct_contab,
            "total_votos":   total_contab,
            "top":           build_top_from_votos(votos_actuales),
            "es_estimacion": False,
        },
        "con_jee": {
            "label":         f"Contabilizadas + JEE · {n_contab + n_jee:,} actas",
            "descripcion":   f"Panel 1 + estimación de votos de {n_jee:,} actas en JEE ({pct_jee:.2f}%), cuyas votos no han sido publicados por ONPE aún.",
            "actas_n":       n_contab + n_jee,
            "actas_pct":     round(pct_contab + pct_jee, 2),
            "total_votos":   total_con_jee,
            "top":           build_top_from_votos(votos_con_jee),
            "es_estimacion": True,
        },
        "proyeccion": {
            "label":         f"Proyección total · {total_actas:,} actas",
            "descripcion":   f"Panel 2 + proyección de las {n_pend:,} actas pendientes ({pct_pend:.2f}%) según el perfil de voto de cada departamento.",
            "actas_n":       total_actas,
            "actas_pct":     100.0,
            "total_votos":   total_proyec,
            "top":           build_top_from_votos(votos_proyec),
            "es_estimacion": True,
        },
        "pendientes": {
            "actas_n":          n_pend,
            "actas_pct":        pct_pend,
            "votos_estimados":  votos_pend_est,
            "por_departamento": pendientes_dep,
        },
        "incertidumbre": incertidumbre,
        "totales": {
            "total_actas":      total_actas,
            "n_contab":         n_contab,
            "n_jee":            n_jee,
            "n_pend":           n_pend,
            "pct_contab":       pct_contab,
            "pct_jee":          pct_jee,
            "pct_pend":         pct_pend,
            "votos_publicados": total_actuales,
        },
    }


EDA_REPORT        = DATA_DIR / "eda_actas_report.json"
ACTA_SAMPLE_IMAGE = Path(__file__).resolve().parent / "acta_comparison.png"
ACTAS_DIR         = DATA_DIR / "actas"
ACTAS_PDF_DIR     = DATA_DIR / "actas_pdf"

# Índice en memoria: id → {file, mesa, dept, prov, dist, estado, validos}
_actas_index: list[dict] = []
_actas_index_built = False
_actas_index_lock = threading.Lock()


def _ensure_actas_index():
    """Construye el índice una sola vez, seguro ante peticiones concurrentes."""
    if _actas_index_built:
        return
    with _actas_index_lock:
        if not _actas_index_built:
            _build_actas_index()


def _build_actas_index():
    global _actas_index, _actas_index_built
    idx = []
    for jf in ACTAS_DIR.rglob("acta_*_e10.json"):
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
            idx.append({
                "id":     str(d.get("id", "")),
                "file":   str(jf),
                "mesa":   d.get("codigoMesa", ""),
                "dept":   d.get("ubigeoNivel01", ""),
                "prov":   d.get("ubigeoNivel02", ""),
                "dist":   d.get("ubigeoNivel03", ""),
                "local":  d.get("nombreLocalVotacion", ""),
                "estado": d.get("descripcionEstadoActa", ""),
                "codigo_estado": d.get("codigoEstadoActa", ""),
                "habiles":  d.get("totalElectoresHabiles") or 0,
                "emitidos": d.get("totalVotosEmitidos") or 0,
                "validos":  d.get("totalVotosValidos") or 0,
                "participacion": d.get("porcentajeParticipacionCiudadana") or 0,
            })
        except Exception:
            pass
    _actas_index = idx
    _actas_index_built = True
    logging.getLogger(__name__).info(f"Actas index built: {len(idx)} entries")


def _pdf_path_for(acta_id: str) -> Path | None:
    for p in ACTAS_PDF_DIR.glob(f"acta_{acta_id}_e10_*.pdf"):
        return p
    return None


def _render_pdf_to_png(pdf_path: Path) -> bytes:
    import fitz
    from PIL import Image
    import io
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    doc.close()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


@app.get("/api/actas-dashboard")
def actas_dashboard():
    if not EDA_REPORT.exists():
        raise HTTPException(status_code=404, detail="EDA report not found. Run eda_actas.py first.")
    return load_json(EDA_REPORT)


@app.get("/api/acta-sample-image")
def acta_sample_image():
    if not ACTA_SAMPLE_IMAGE.exists():
        raise HTTPException(status_code=404, detail="Sample image not found.")
    return FileResponse(ACTA_SAMPLE_IMAGE, media_type="image/png")


@app.get("/api/actas/search")
def search_actas(
    dept: str = "",
    mesa: str = "",
    dist: str = "",
    estado: str = "",
    page: int = 0,
    size: int = 30,
):
    _ensure_actas_index()

    results = _actas_index
    dept_n  = norm(dept)
    mesa_n  = mesa.strip().lstrip("0")
    dist_n  = norm(dist)
    est_n   = estado.strip().upper()

    if dept_n:
        results = [r for r in results if dept_n in norm(r["dept"])]
    if dist_n:
        results = [r for r in results if dist_n in norm(r["dist"])]
    if mesa_n:
        results = [r for r in results if mesa_n in r["mesa"].lstrip("0")]
    if est_n:
        results = [r for r in results if r["codigo_estado"] == est_n]

    total = len(results)
    page_items = results[page * size: (page + 1) * size]

    # Marcar cuáles tienen PDF local
    out = []
    for r in page_items:
        item = dict(r)
        item.pop("file", None)
        item["tiene_pdf"] = _pdf_path_for(r["id"]) is not None
        out.append(item)

    return {"total": total, "page": page, "size": size, "items": out}


@app.get("/api/actas/{acta_id}/data")
def get_acta_data(acta_id: str):
    _ensure_actas_index()
    entry = next((r for r in _actas_index if r["id"] == acta_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    return load_json(Path(entry["file"]))


@app.get("/api/actas/{acta_id}/image")
def get_acta_image(acta_id: str):
    pdf = _pdf_path_for(acta_id)
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF no disponible para esta acta")
    png_bytes = _render_pdf_to_png(pdf)
    return Response(content=png_bytes, media_type="image/png")


@app.post("/api/refresh")
async def refresh():
    """Descarga datos frescos de ONPE y reconstruye el cache (atómico con lock).

    Tiene un cooldown para que el endpoint público no pueda usarse para
    amplificar tráfico hacia ONPE: dentro de la ventana devuelve el estado actual
    sin re-descargar (el loop de fondo refresca cada 5 min de todas formas).
    """
    global _last_refresh_ts
    now = time.monotonic()
    en_cooldown = (now - _last_refresh_ts) < REFRESH_COOLDOWN
    if not en_cooldown:
        _last_refresh_ts = now
        await _fetch_and_invalidate()
        _load_historial()
    data = get_data()
    return {"ok": True, "cooldown": en_cooldown, "status": {
        "presidencial_mapa": len(data["presidencial"]["mapa"]),
        "senado_reg_mapa": len(data["senado_regional"]["mapa"]),
        "historial_puntos": len(_historial),
    }}


@app.post("/api/historial/reload", include_in_schema=False)
def reload_historial():
    """Recarga historial.json sin tocar el cache."""
    _load_historial()
    return {"ok": True, "puntos": len(_historial)}


# ── Frontend estático (build de React) ─────────────────
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # Archivos estáticos en la raíz del dist (GeoJSON, favicon, iconos, etc.)
    _STATIC_EXTS = {".geojson", ".svg", ".ico", ".png", ".webp", ".txt", ".json"}

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if candidate.exists() and candidate.is_file() and candidate.suffix in _STATIC_EXTS:
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"error": "Frontend no compilado. Ejecuta: cd frontend && npm run build"}
