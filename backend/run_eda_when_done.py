"""
Monitorea scraper_actas.py y ejecuta eda_actas.py cuando termina.
"""
import subprocess, time, sys
from pathlib import Path

LOG = Path(__file__).parent / "scraper_actas_run.log"
EDA = Path(__file__).parent / "eda_actas.py"
PYTHON = sys.executable

print("Monitoreando scraper... (Ctrl+C para salir)")

last_size = 0
idle_rounds = 0

while True:
    time.sleep(60)
    size = LOG.stat().st_size if LOG.exists() else 0
    content = LOG.read_text(encoding="utf-8", errors="ignore") if LOG.exists() else ""

    if "DONE. Stats:" in content:
        print("\n✓ Scraper terminó. Lanzando EDA...")
        break

    if size == last_size:
        idle_rounds += 1
        if idle_rounds >= 10:  # 10 min sin cambios = scraper colgado o terminado
            print(f"\nSin actividad en 10 min. Lanzando EDA de todas formas...")
            break
    else:
        idle_rounds = 0
        last_size = size

    # Mostrar progreso
    lines = content.strip().split("\n")
    for line in reversed(lines[-5:]):
        if "INFO" in line:
            print(f"  {line.strip()}")
            break

subprocess.run([PYTHON, str(EDA)], check=False)
