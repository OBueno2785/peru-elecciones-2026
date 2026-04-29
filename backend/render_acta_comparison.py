"""
Renderiza una acta PDF y la compara lado a lado con los datos JSON registrados.
"""
import json
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

PDF_PATH  = Path(__file__).parent / "data/actas_pdf/acta_22801020510_e10_69dcd90ad7b6147f63e6e31a.pdf"
JSON_PATH = Path(__file__).parent / "data/actas/AMAZONAS/BAGUA/BAGUA/acta_22801020510_e10.json"
OUT_PATH  = Path(__file__).parent / "acta_comparison.png"

# ── 1. Convertir primera página PDF a PIL Image ──────────────────────────────
doc = fitz.open(str(PDF_PATH))
page = doc[0]
mat = fitz.Matrix(1.6, 1.6)  # 1.6x zoom → ~130 dpi
pix = page.get_pixmap(matrix=mat, alpha=False)
acta_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
doc.close()

print(f"Acta image: {acta_img.size}")

# ── 2. Cargar datos JSON ──────────────────────────────────────────────────────
data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

mesa         = data["codigoMesa"]
local        = data["nombreLocalVotacion"]
dept         = data["ubigeoNivel01"]
prov         = data["ubigeoNivel02"]
dist         = data["ubigeoNivel03"]
habiles      = data["totalElectoresHabiles"]
emitidos     = data["totalVotosEmitidos"]
validos      = data["totalVotosValidos"]
participacion= data["porcentajeParticipacionCiudadana"]
estado       = data["descripcionEstadoActa"]

detalle = data.get("detalle", [])
partidos = [d for d in detalle if d.get("grafico") == 1 and d.get("nvotos", 0) > 0]
partidos.sort(key=lambda x: -x["nvotos"])
blancos = next((d["nvotos"] for d in detalle if d["descripcion"] == "VOTOS EN BLANCO"), 0)
nulos   = next((d["nvotos"] for d in detalle if d["descripcion"] == "VOTOS NULOS"), 0)

# ── 3. Construir panel de datos ───────────────────────────────────────────────
PANEL_W = 900
PANEL_H = acta_img.height
MARGIN  = 20
LINE_H  = 28

panel = Image.new("RGB", (PANEL_W, PANEL_H), (255, 255, 255))
draw  = ImageDraw.Draw(panel)

try:
    font_title = ImageFont.truetype("arial.ttf", 18)
    font_head  = ImageFont.truetype("arialbd.ttf", 14)
    font_body  = ImageFont.truetype("arial.ttf", 13)
    font_small = ImageFont.truetype("arial.ttf", 11)
except Exception:
    font_title = ImageFont.load_default(size=18)
    font_head  = ImageFont.load_default(size=14)
    font_body  = ImageFont.load_default(size=13)
    font_small = ImageFont.load_default(size=11)

y = MARGIN
BLUE   = (30, 58, 138)
GREEN  = (21, 128, 61)
RED    = (185, 28, 28)
GRAY   = (107, 114, 128)
BLACK  = (17, 24, 39)
LIGHT  = (243, 244, 246)

def text(txt, x, yy, font=None, fill=BLACK):
    draw.text((x, yy), txt, font=font or font_body, fill=fill)
    return yy + LINE_H

def hline(yy, color=(209, 213, 219)):
    draw.line([(MARGIN, yy), (PANEL_W - MARGIN, yy)], fill=color, width=1)
    return yy + 8

# Header
draw.rectangle([(0, 0), (PANEL_W, 55)], fill=BLUE)
draw.text((MARGIN, 10), "DATOS REGISTRADOS EN EL SISTEMA — ONPE 2026", font=font_head, fill=(255, 255, 255))
draw.text((MARGIN, 32), "Elección Presidencial  ·  idEleccion=10", font=font_small, fill=(147, 197, 253))
y = 65

# Identificación
y = text(f"Mesa:          {mesa}", MARGIN, y, font_head, BLUE)
y = text(f"Local:         {local}", MARGIN, y)
y = text(f"Ubigeo:        {dept} > {prov} > {dist}", MARGIN, y)
y = text(f"Estado:        {estado}", MARGIN, y, fill=GREEN)
y = hline(y)

# Totales
y = text("TOTALES", MARGIN, y, font_head, BLUE)
draw.rectangle([(MARGIN, y), (PANEL_W - MARGIN, y + LINE_H * 4 + 10)], fill=LIGHT, outline=(209, 213, 219))
y += 6
y = text(f"  Electores hábiles:  {habiles:,}", MARGIN, y)
y = text(f"  Votos emitidos:     {emitidos:,}   ({participacion:.2f}%)", MARGIN, y)
y = text(f"  Votos válidos:      {validos:,}", MARGIN, y, fill=GREEN)
y = text(f"  Votos en blanco:    {blancos:,}  |  Nulos: {nulos:,}", MARGIN, y, fill=GRAY)
y += 6
y = hline(y)

# Barra de participación
bar_w = PANEL_W - 2 * MARGIN
pct_px = int(bar_w * min(participacion, 100) / 100)
draw.rectangle([(MARGIN, y), (MARGIN + bar_w, y + 14)], fill=(209, 213, 219))
draw.rectangle([(MARGIN, y), (MARGIN + pct_px, y + 14)], fill=(59, 130, 246))
draw.text((MARGIN + bar_w // 2 - 30, y + 1), f"Participación {participacion:.1f}%", font=font_small, fill=BLACK)
y += 22
y = hline(y)

# Resultados por partido
y = text("RESULTADOS POR PARTIDO (grafico=1, votos > 0)", MARGIN, y, font_head, BLUE)
max_votos = partidos[0]["nvotos"] if partidos else 1
bar_max_w = PANEL_W - 2 * MARGIN - 200

for p in partidos[:18]:
    nombre = p["descripcion"]
    votos  = p["nvotos"]
    pct_v  = p.get("nporcentajeVotosValidos") or 0
    bar_len = int(bar_max_w * votos / max_votos)

    # Nombre truncado
    nombre_short = nombre[:30] + "…" if len(nombre) > 30 else nombre
    draw.text((MARGIN, y + 4), nombre_short, font=font_small, fill=BLACK)

    # Barra
    bx = MARGIN + 200
    draw.rectangle([(bx, y + 4), (bx + bar_max_w, y + LINE_H - 4)], fill=(229, 231, 235))
    bar_color = (220, 38, 38) if votos == max_votos else (59, 130, 246)
    draw.rectangle([(bx, y + 4), (bx + bar_len, y + LINE_H - 4)], fill=bar_color)
    draw.text((bx + bar_len + 4, y + 4), f"{votos}  ({pct_v:.1f}%)", font=font_small, fill=GRAY)

    y += LINE_H
    if y + LINE_H > PANEL_H - 40:
        break

y = hline(y)

# Verificación de suma
sum_partidos = sum(p["nvotos"] for p in partidos)
match = abs(sum_partidos - validos) <= 2
color_check = GREEN if match else RED
symbol = "✓" if match else "✗"
y = text(f"{symbol} Suma partidos: {sum_partidos}  vs  válidos registrados: {validos}", MARGIN, y, fill=color_check)
y = text(f"  Suma emitidos (blancos+nulos+validos): {sum_partidos + blancos + nulos}  vs  emitidos: {emitidos}",
         MARGIN, y, font=font_small, fill=GRAY)

# Footer
draw.rectangle([(0, PANEL_H - 28), (PANEL_W, PANEL_H)], fill=BLUE)
draw.text((MARGIN, PANEL_H - 20), f"Archivo: acta_{data['id']}_e{data['idEleccion']}.json  |  Solución: {data.get('descripcionSolucionTecnologica','')}",
          font=font_small, fill=(147, 197, 253))

# ── 4. Unir imágenes ─────────────────────────────────────────────────────────
total_w = acta_img.width + PANEL_W + 10
total_h = max(acta_img.height, PANEL_H)
canvas   = Image.new("RGB", (total_w, total_h), (229, 231, 235))

canvas.paste(acta_img, (0, 0))
canvas.paste(panel,    (acta_img.width + 10, 0))

# Línea divisoria
cdraw = ImageDraw.Draw(canvas)
cdraw.rectangle([(acta_img.width + 2, 0), (acta_img.width + 8, total_h)], fill=(100, 116, 139))

canvas.save(str(OUT_PATH), "PNG", optimize=True)
print(f"\nGuardado en: {OUT_PATH}")
print(f"Tamaño final: {canvas.size[0]}x{canvas.size[1]} px")
