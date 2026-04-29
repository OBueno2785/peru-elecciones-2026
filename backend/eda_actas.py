"""
Análisis Exploratorio de Actas - Elecciones Perú 2026
Lee todos los JSON descargados por scraper_actas.py y produce un reporte completo.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "actas"
OUT_FILE = Path(__file__).parent / "data" / "eda_actas_report.json"
OUT_TXT  = Path(__file__).parent / "data" / "eda_actas_report.txt"

ESTADOS = {
    "C": "Contabilizada", "O": "Observada", "P": "Pendiente",
    "E": "Enviada JEE", "T": "Digitalizada", "D": "Digitada", "": "Desconocido"
}


# -- helpers ------------------------------------------------------------------

def pct(num, den):
    return round(num / den * 100, 2) if den else 0


def stdev(vals):
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return math.sqrt(sum((x - mean) ** 2 for x in vals) / len(vals))


def median(vals):
    s = sorted(vals)
    n = len(s)
    return (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]


# -- carga de datos ------------------------------------------------------------

def load_all_actas() -> list[dict]:
    actas = []
    for json_file in DATA_DIR.rglob("acta_*_e10.json"):  # solo presidencial
        try:
            raw = json.loads(json_file.read_text(encoding="utf-8"))
            raw["_file"] = str(json_file.relative_to(DATA_DIR))
            actas.append(raw)
        except Exception as e:
            print(f"  WARN: {json_file}: {e}")
    return actas


# -- análisis -----------------------------------------------------------------

def analizar(actas: list[dict]) -> dict:
    total = len(actas)
    print(f"Total actas cargadas: {total}")

    # -- 1. Distribución por estado -----------------------------------------
    por_estado = defaultdict(int)
    for a in actas:
        por_estado[a.get("codigoEstadoActa", "")] += 1

    # -- 2. Estadísticas de votos -------------------------------------------
    habiles, emitidos, validos, participacion = [], [], [], []
    for a in actas:
        h = a.get("totalElectoresHabiles") or 0
        e = a.get("totalVotosEmitidos") or 0
        v = a.get("totalVotosValidos") or 0
        p = a.get("porcentajeParticipacionCiudadana") or 0
        if h > 0:
            habiles.append(h)
            emitidos.append(e)
            validos.append(v)
            participacion.append(p)

    def stats(vals, label):
        if not vals:
            return {}
        return {
            "n": len(vals),
            "total": sum(vals),
            "mean": round(sum(vals) / len(vals), 2),
            "median": round(median(vals), 2),
            "stdev": round(stdev(vals), 2),
            "min": min(vals),
            "max": max(vals),
        }

    # -- 3. Votos por partido -----------------------------------------------
    votos_partido = defaultdict(int)
    actas_partido = defaultdict(int)
    for a in actas:
        for d in (a.get("detalle") or []):
            desc = d.get("descripcion", "?")
            votos = d.get("nvotos") or 0
            if votos > 0 or d.get("grafico", 0) == 1:
                votos_partido[desc] += votos
                actas_partido[desc] += 1

    total_validos_global = votos_partido.get("VOTOS EN BLANCO", 0)
    partidos_reales = {k: v for k, v in votos_partido.items()
                       if k not in ("VOTOS EN BLANCO", "VOTOS NULOS", "VOTOS IMPUGNADOS")}
    total_votos_validos = sum(partidos_reales.values())

    top_partidos = sorted(partidos_reales.items(), key=lambda x: -x[1])[:15]

    # -- 4. Consistencia numérica -------------------------------------------
    inconsistencias = []
    alertas = []
    for a in actas:
        acta_id = a.get("id", "?")
        mesa = a.get("codigoMesa", "?")
        h = a.get("totalElectoresHabiles") or 0
        e = a.get("totalVotosEmitidos") or 0
        v = a.get("totalVotosValidos") or 0
        p = a.get("porcentajeParticipacionCiudadana") or 0

        detalle = a.get("detalle") or []
        # Solo sumar partidos reales (grafico=1), excluye blancos/nulos
        sum_partidos = sum((d.get("nvotos") or 0) for d in detalle if d.get("grafico", 0) == 1)
        # Suma total incluyendo blancos/nulos = debería coincidir con votos emitidos
        sum_todos = sum((d.get("nvotos") or 0) for d in detalle)

        issues = []
        # votos emitidos > electores habiles
        if h > 0 and e > h:
            issues.append(f"emitidos({e}) > habiles({h})")
        # votos validos > votos emitidos
        if e > 0 and v > e:
            issues.append(f"validos({v}) > emitidos({e})")
        # suma de partidos no coincide con votos válidos
        if detalle and sum_partidos > 0 and abs(sum_partidos - v) > 2:
            issues.append(f"suma_partidos({sum_partidos}) != validos({v})")
        # suma total no coincide con votos emitidos
        if detalle and sum_todos > 0 and e > 0 and abs(sum_todos - e) > 2:
            issues.append(f"suma_total_detalle({sum_todos}) != emitidos({e})")
        # participación > 100%
        if p > 100:
            issues.append(f"participacion({p}%) > 100%")
        # participación inconsistente con emitidos/habiles
        if h > 0 and e > 0:
            calc_pct = round(e / h * 100, 3)
            if abs(calc_pct - p) > 1.0:
                issues.append(f"pct_calculado({calc_pct}) != pct_reportado({p})")

        if issues:
            inconsistencias.append({
                "id": acta_id, "mesa": mesa,
                "dept": a.get("ubigeoNivel01"), "dist": a.get("ubigeoNivel03"),
                "issues": issues,
            })

        # Alertas: participación muy alta o muy baja
        if h > 0 and p > 95:
            alertas.append({"tipo": "participacion_alta", "mesa": mesa, "pct": p, "dist": a.get("ubigeoNivel03")})
        elif h > 0 and p < 20 and e > 0:
            alertas.append({"tipo": "participacion_baja", "mesa": mesa, "pct": p, "dist": a.get("ubigeoNivel03")})

    # -- 5. Distribución geográfica -----------------------------------------
    por_dept = defaultdict(lambda: {"actas": 0, "votos": 0, "contabilizada": 0})
    for a in actas:
        dept = a.get("ubigeoNivel01", "SIN DATOS")
        por_dept[dept]["actas"] += 1
        por_dept[dept]["votos"] += (a.get("totalVotosValidos") or 0)
        if a.get("codigoEstadoActa") == "C":
            por_dept[dept]["contabilizada"] += 1

    # -- Resumen ------------------------------------------------------------
    return {
        "resumen_general": {
            "total_actas_analizadas": total,
            "por_estado": {ESTADOS.get(k, k): v for k, v in por_estado.items()},
            "pct_contabilizadas": pct(por_estado.get("C", 0), total),
            "pct_observadas": pct(por_estado.get("O", 0), total),
            "pct_pendientes": pct(por_estado.get("P", 0), total),
        },
        "estadisticas_votos": {
            "electores_habiles": stats(habiles, "habiles"),
            "votos_emitidos": stats(emitidos, "emitidos"),
            "votos_validos": stats(validos, "validos"),
            "participacion_pct": stats(participacion, "pct"),
            "total_votos_validos_global": total_votos_validos,
            "total_actas_con_datos": len(habiles),
        },
        "top_15_partidos": [
            {
                "partido": p,
                "votos": v,
                "pct_sobre_validos": pct(v, total_votos_validos),
                "actas_con_votos": actas_partido[p],
            }
            for p, v in top_partidos
        ],
        "votos_especiales": {
            "en_blanco": votos_partido.get("VOTOS EN BLANCO", 0),
            "nulos": votos_partido.get("VOTOS NULOS", 0),
            "impugnados": votos_partido.get("VOTOS IMPUGNADOS", 0),
        },
        "consistencia": {
            "actas_con_inconsistencias": len(inconsistencias),
            "pct_inconsistencias": pct(len(inconsistencias), total),
            "tipos_frecuentes": _contar_tipos(inconsistencias),
            "muestra_inconsistencias": inconsistencias[:20],
        },
        "alertas_participacion": {
            "total_alertas": len(alertas),
            "alta_participacion_gt95": sum(1 for a in alertas if a["tipo"] == "participacion_alta"),
            "baja_participacion_lt20": sum(1 for a in alertas if a["tipo"] == "participacion_baja"),
            "muestra": alertas[:20],
        },
        "por_departamento": [
            {
                "departamento": dept,
                "actas": v["actas"],
                "actas_contabilizadas": v["contabilizada"],
                "pct_contabilizadas": pct(v["contabilizada"], v["actas"]),
                "total_votos_validos": v["votos"],
            }
            for dept, v in sorted(por_dept.items(), key=lambda x: -x[1]["votos"])
        ],
    }


def _contar_tipos(inconsistencias):
    tipos = defaultdict(int)
    for inc in inconsistencias:
        for issue in inc["issues"]:
            for keyword in ["emitidos > habiles", "validos > emitidos", "suma_partidos", "suma_total_detalle", "participacion", "pct_calculado"]:
                if keyword in issue:
                    tipos[keyword] += 1
    return dict(sorted(tipos.items(), key=lambda x: -x[1]))


# -- reporte texto -------------------------------------------------------------

def print_report(r: dict, file=None):
    def pr(*args):
        print(*args)
        if file:
            print(*args, file=file)

    sep = "=" * 65

    pr(sep)
    pr("ANÁLISIS EXPLORATORIO DE ACTAS - ELECCIONES PERÚ 2026")
    pr("       Elección Presidencial (idEleccion=10)")
    pr(sep)

    g = r["resumen_general"]
    pr(f"\n{'-'*50}")
    pr("1. RESUMEN GENERAL")
    pr(f"{'-'*50}")
    pr(f"  Total actas analizadas : {g['total_actas_analizadas']:>8,}")
    for estado, n in g["por_estado"].items():
        pr(f"  {estado:<22}: {n:>8,}  ({pct(n, g['total_actas_analizadas']):.1f}%)")

    ev = r["estadisticas_votos"]
    pr(f"\n{'-'*50}")
    pr("2. ESTADÍSTICAS DE VOTOS POR MESA")
    pr(f"{'-'*50}")
    pr(f"  Actas con datos        : {ev['total_actas_con_datos']:>8,}")
    pr(f"  Total votos válidos    : {ev['total_votos_validos_global']:>8,}")
    for label, key in [
        ("Electores hábiles", "electores_habiles"),
        ("Votos emitidos", "votos_emitidos"),
        ("Votos válidos", "votos_validos"),
        ("Participación (%)", "participacion_pct"),
    ]:
        s = ev[key]
        if s:
            pr(f"\n  {label}:")
            pr(f"    Total  = {s.get('total', 0):>10,.0f}   Media  = {s['mean']:.1f}")
            pr(f"    Mediana= {s['median']:.1f}   Stdev  = {s['stdev']:.1f}")
            pr(f"    Min    = {s['min']:.1f}   Max    = {s['max']:.1f}")

    pr(f"\n{'-'*50}")
    pr("3. TOP 15 PARTIDOS / CANDIDATOS (por votos válidos)")
    pr(f"{'-'*50}")
    pr(f"  {'#':<3} {'Partido/Candidato':<40} {'Votos':>9} {'%':>7}")
    pr(f"  {'-'*3} {'-'*40} {'-'*9} {'-'*7}")
    for i, p_data in enumerate(r["top_15_partidos"], 1):
        pr(f"  {i:<3} {p_data['partido'][:40]:<40} {p_data['votos']:>9,} {p_data['pct_sobre_validos']:>6.2f}%")

    ve = r["votos_especiales"]
    total_v = ev["total_votos_validos_global"] or 1
    pr(f"\n  Votos en blanco : {ve['en_blanco']:>8,}  ({pct(ve['en_blanco'], total_v):.2f}% de válidos)")
    pr(f"  Votos nulos     : {ve['nulos']:>8,}")
    pr(f"  Votos impugnados: {ve['impugnados']:>8,}")

    c = r["consistencia"]
    pr(f"\n{'-'*50}")
    pr("4. CONSISTENCIA NUMÉRICA")
    pr(f"{'-'*50}")
    pr(f"  Actas con inconsistencias: {c['actas_con_inconsistencias']:,} ({c['pct_inconsistencias']:.2f}%)")
    if c["tipos_frecuentes"]:
        pr("  Tipos de inconsistencia:")
        for tipo, n in c["tipos_frecuentes"].items():
            pr(f"    • {tipo}: {n}")
    if c["muestra_inconsistencias"]:
        pr(f"\n  Muestra (primeras 10):")
        for inc in c["muestra_inconsistencias"][:10]:
            pr(f"    Mesa {inc['mesa']} ({inc['dist']}, {inc['dept']}): {', '.join(inc['issues'])}")

    al = r["alertas_participacion"]
    pr(f"\n{'-'*50}")
    pr("5. ALERTAS DE PARTICIPACIÓN")
    pr(f"{'-'*50}")
    pr(f"  Participación > 95%: {al['alta_participacion_gt95']:,} mesas")
    pr(f"  Participación < 20%: {al['baja_participacion_lt20']:,} mesas")

    pr(f"\n{'-'*50}")
    pr("6. DISTRIBUCIÓN POR DEPARTAMENTO")
    pr(f"{'-'*50}")
    pr(f"  {'Departamento':<25} {'Actas':>7} {'Contab.':>8} {'%Cont.':>7} {'V.Válidos':>12}")
    pr(f"  {'-'*25} {'-'*7} {'-'*8} {'-'*7} {'-'*12}")
    for d in r["por_departamento"]:
        pr(f"  {d['departamento'][:25]:<25} {d['actas']:>7,} {d['actas_contabilizadas']:>8,} {d['pct_contabilizadas']:>6.1f}% {d['total_votos_validos']:>12,}")

    pr(f"\n{sep}")
    pr("FIN DEL REPORTE")
    pr(sep)


# -- main ----------------------------------------------------------------------

if __name__ == "__main__":
    print("Cargando actas...")
    actas = load_all_actas()

    if not actas:
        print("No se encontraron actas. Verifica que scraper_actas.py haya descargado datos.")
        exit(1)

    print(f"Analizando {len(actas):,} actas...")
    report = analizar(actas)

    # Guardar JSON
    OUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Reporte JSON: {OUT_FILE}")

    # Guardar y mostrar texto
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        print_report(report, file=f)
    # También imprimir en consola con encoding seguro
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"Reporte TXT:  {OUT_TXT}\n")

    print_report(report)  # después de reconfigurar stdout
