"""
Scraper de Actas ONPE 2026
Descarga datos JSON de cada acta por centro de votación.
Para actas observadas/pendientes también descarga el PDF desde S3.

Endpoints descubiertos:
  /ubigeos/departamentos?idEleccion=10&idAmbitoGeografico=1
  /ubigeos/provincias?idEleccion=10&idAmbitoGeografico=1&idUbigeoDepartamento=XXXXXX
  /ubigeos/distritos?idEleccion=10&idAmbitoGeografico=1&idUbigeoProvincia=XXXXXX
  /actas?pagina=N&tamanio=100&idAmbitoGeografico=1&idUbigeo=DISTRICT_NUMERIC
  /actas/{id}   → JSON completo con detalle de votos y campo archivos[]
  /actas/file?id={archivos[0].id}  → URL S3 firmada del PDF
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from playwright.async_api import async_playwright, Page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("scraper_actas.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BASE = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend"
BASE_SITE = "https://resultadoelectoral.onpe.gob.pe"
DATA_DIR = Path(__file__).parent / "data" / "actas"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR = Path(__file__).parent / "data" / "actas_pdf"
PDF_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = Path(__file__).parent / "data" / "actas_progress.json"

ID_ELECCION = 10  # Presidencial
AMBITO = 1        # Perú
PAGE_SIZE = 100
MAX_WORKERS = 4   # tabs paralelos para descargas


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"completed_districts": [], "stats": {"json": 0, "pdf": 0, "errors": 0}}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


async def api_get(page: Page, path: str) -> dict | None:
    url = BASE + path
    try:
        result = await page.evaluate(f"""async () => {{
            const r = await fetch("{url}", {{
                headers: {{"content-type": "application/json", "accept": "*/*"}}
            }});
            const ct = r.headers.get("content-type") || "";
            if (ct.includes("json")) return await r.json();
            return {{_error: r.status, _ct: ct}};
        }}""")
        if "_error" in result:
            log.warning(f"Non-JSON {result['_error']} for {path}")
            return None
        return result
    except Exception as e:
        log.error(f"api_get error {path}: {e}")
        return None


async def download_pdf(page: Page, file_id: str, dest: Path) -> bool:
    if dest.exists():
        return True
    url_r = await api_get(page, f"/actas/file?id={file_id}")
    if not url_r or not url_r.get("data"):
        return False
    s3_url = url_r["data"]
    try:
        result = await page.evaluate(f"""async () => {{
            const r = await fetch("{s3_url}");
            if (!r.ok) return {{error: r.status}};
            const buf = await r.arrayBuffer();
            return {{size: buf.byteLength, data: Array.from(new Uint8Array(buf))}};
        }}""")
        if "error" in result:
            log.warning(f"PDF download error {result['error']} for {file_id}")
            return False
        dest.write_bytes(bytes(result["data"]))
        return True
    except Exception as e:
        log.error(f"PDF download exception {file_id}: {e}")
        return False


async def process_acta(page: Page, acta: dict, dist_dir: Path, progress: dict) -> tuple[str, bool]:
    acta_id = acta["id"]
    codigo_mesa = acta.get("codigoMesa", "")
    id_eleccion = acta.get("idEleccion", 10)
    estado = acta.get("codigoEstadoActa", "")

    json_path = dist_dir / f"acta_{acta_id}_e{id_eleccion}.json"

    # Always get full JSON detail
    if not json_path.exists():
        detail = await api_get(page, f"/actas/{acta_id}")
        if detail and detail.get("data"):
            json_path.write_text(json.dumps(detail["data"], ensure_ascii=False, indent=2), encoding="utf-8")
            progress["stats"]["json"] += 1
            archivos = detail["data"].get("archivos", [])
        else:
            archivos = []
    else:
        try:
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            archivos = saved.get("archivos", [])
        except Exception:
            archivos = []

    # Download PDF only for observada/pendiente (contabilizada ya tiene JSON con votos)
    pdf_downloaded = False
    needs_pdf = estado in ("O", "P", "")  # Observada, Pendiente, o desconocido
    if needs_pdf and archivos:
        for archivo in archivos:
            file_id = archivo.get("id", "")
            if not file_id:
                continue
            pdf_path = PDF_DIR / f"acta_{acta_id}_e{id_eleccion}_{file_id}.pdf"
            ok = await download_pdf(page, file_id, pdf_path)
            if ok:
                progress["stats"]["pdf"] += 1
                pdf_downloaded = True
            break  # First file is the main acta image

    return estado, pdf_downloaded


async def get_districts_for_dept(page: Page, dept_ubigeo: str, prov_ubigeo: str) -> list[dict]:
    r = await api_get(page, f"/ubigeos/distritos?idEleccion={ID_ELECCION}&idAmbitoGeografico={AMBITO}&idUbigeoProvincia={prov_ubigeo}")
    if r and r.get("data"):
        return r["data"]
    return []


async def process_district(page: Page, district: dict, dept_nombre: str, prov_nombre: str, progress: dict):
    dist_ubigeo_str = district["ubigeo"]
    dist_nombre = district["nombre"]
    dist_ubigeo_int = int(dist_ubigeo_str)

    dist_key = f"{dept_nombre}/{prov_nombre}/{dist_nombre}_{dist_ubigeo_str}"
    if dist_key in progress["completed_districts"]:
        log.info(f"Skip (done): {dist_key}")
        return

    log.info(f"Processing district: {dept_nombre} > {prov_nombre} > {dist_nombre} (ubigeo={dist_ubigeo_str})")

    dist_dir = DATA_DIR / dept_nombre.replace("/", "_") / prov_nombre.replace("/", "_") / dist_nombre.replace("/", "_")
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Get total pages
    r0 = await api_get(page, f"/actas?pagina=0&tamanio={PAGE_SIZE}&idAmbitoGeografico={AMBITO}&idUbigeo={dist_ubigeo_int}")
    if not r0 or not r0.get("data"):
        log.warning(f"No actas data for district {dist_ubigeo_str}")
        progress["completed_districts"].append(dist_key)
        save_progress(progress)
        return

    data0 = r0["data"]
    total = data0.get("totalRegistros", 0)
    total_pages = data0.get("totalPaginas", 0)
    contabilizada = data0.get("contabilizada", 0)
    observada = data0.get("observada", 0)
    pendiente = data0.get("pendiente", 0)

    log.info(f"  Total actas: {total} | Contabilizada: {contabilizada} | Observada: {observada} | Pendiente: {pendiente} | Pages: {total_pages}")

    # Save district summary
    summary_path = dist_dir / "_summary.json"
    summary = {
        "ubigeo": dist_ubigeo_str,
        "nombre": dist_nombre,
        "departamento": dept_nombre,
        "provincia": prov_nombre,
        "totalActas": total,
        "contabilizada": contabilizada,
        "observada": observada,
        "pendiente": pendiente,
        "idEleccion": ID_ELECCION,
        "timestamp": int(time.time()),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    all_actas = list(data0.get("content", []))

    for page_num in range(1, total_pages):
        rp = await api_get(page, f"/actas?pagina={page_num}&tamanio={PAGE_SIZE}&idAmbitoGeografico={AMBITO}&idUbigeo={dist_ubigeo_int}")
        if rp and rp.get("data"):
            all_actas.extend(rp["data"].get("content", []))
        await asyncio.sleep(0.2)

    log.info(f"  Fetched {len(all_actas)} actas records for {dist_nombre}")

    # Process actas in parallel batches using semaphore
    sem = asyncio.Semaphore(MAX_WORKERS)

    async def process_one(acta, idx):
        async with sem:
            try:
                estado, pdf_ok = await process_acta(page, acta, dist_dir, progress)
            except Exception as e:
                log.error(f"Error processing acta {acta.get('id')}: {e}")
                progress["stats"]["errors"] += 1
            if idx % 50 == 0:
                save_progress(progress)
                log.info(f"  Progress {idx+1}/{len(all_actas)} | JSON: {progress['stats']['json']} | PDF: {progress['stats']['pdf']}")

    tasks = [process_one(acta, i) for i, acta in enumerate(all_actas)]
    await asyncio.gather(*tasks)

    progress["completed_districts"].append(dist_key)
    save_progress(progress)
    log.info(f"  District complete: {dist_nombre}")


async def main():
    log.info("=" * 60)
    log.info("SCRAPER ACTAS ONPE 2026")
    log.info("=" * 60)

    progress = load_progress()
    log.info(f"Progress loaded: {len(progress['completed_districts'])} districts done, stats={progress['stats']}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        log.info("Initializing browser session...")
        await page.goto(f"{BASE_SITE}/main/actas", wait_until="networkidle", timeout=40000)
        await asyncio.sleep(5)
        log.info("Session ready.")

        # Get all departments
        r = await api_get(page, f"/ubigeos/departamentos?idEleccion={ID_ELECCION}&idAmbitoGeografico={AMBITO}")
        if not r or not r.get("data"):
            log.error("Could not fetch departments!")
            return
        depts = r["data"]
        log.info(f"Departments: {len(depts)}")

        for dept in depts:
            dept_ubigeo = dept["ubigeo"]
            dept_nombre = dept["nombre"]
            log.info(f"\n>>> Department: {dept_nombre} ({dept_ubigeo})")

            # Get provinces
            rp = await api_get(page, f"/ubigeos/provincias?idEleccion={ID_ELECCION}&idAmbitoGeografico={AMBITO}&idUbigeoDepartamento={dept_ubigeo}")
            if not rp or not rp.get("data"):
                log.warning(f"No provinces for {dept_nombre}")
                continue
            provinces = rp["data"]

            for prov in provinces:
                prov_ubigeo = prov["ubigeo"]
                prov_nombre = prov["nombre"]
                log.info(f"  Province: {prov_nombre} ({prov_ubigeo})")

                # Get districts
                districts = await get_districts_for_dept(page, dept_ubigeo, prov_ubigeo)
                log.info(f"  Districts: {len(districts)}")

                for district in districts:
                    await process_district(page, district, dept_nombre, prov_nombre, progress)
                    await asyncio.sleep(0.3)

        await browser.close()

    log.info("=" * 60)
    log.info(f"DONE. Stats: {progress['stats']}")
    log.info(f"Districts completed: {len(progress['completed_districts'])}")


if __name__ == "__main__":
    asyncio.run(main())
