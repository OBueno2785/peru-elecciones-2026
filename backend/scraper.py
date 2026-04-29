"""
Scraper ONPE 2026
Navega la SPA de resultadoelectoral.onpe.gob.pe con Playwright headless,
intercepta todas las llamadas XHR/Fetch del Angular app,
y guarda los datos en /data/ como JSON.
"""
import asyncio
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE_URL = "https://resultadoelectoral.onpe.gob.pe"

# URLs de las vistas que queremos navegar
VIEWS = {
    "presidencial": f"{BASE_URL}/main/resumen/presidencial",
    "senado_nacional": f"{BASE_URL}/main/resumen/senado-nacional",
    "senado_regional": f"{BASE_URL}/main/resumen/senado-regional",
    "resumen": f"{BASE_URL}/main/resumen",
}

captured = {}  # {url: response_body}


def should_capture(url: str) -> bool:
    """Captura solo llamadas XHR/API que traen datos de elecciones."""
    parsed = urlparse(url)
    # Ignorar analytics, fonts, CDN, etc.
    ignore = [
        "google", "gstatic", "googleapis", "analytics",
        "googletagmanager", "amcharts", "jsdelivr",
        "favicon", ".css", ".js", ".woff", ".png", ".ico",
        "s3.amazonaws.com",
    ]
    return not any(ig in url for ig in ignore)


async def capture_network(page, url: str, tag: str):
    """Navega a una URL y captura todas las respuestas de red."""
    responses = {}

    async def on_response(response):
        resp_url = response.url
        if not should_capture(resp_url):
            return
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type and "text" not in content_type:
            return
        try:
            body = await response.text()
            if body and len(body) > 50:
                parsed = json.loads(body)
                responses[resp_url] = parsed
                print(f"  [CAPTURADO] {resp_url[:90]}")
        except Exception:
            pass

    page.on("response", on_response)

    print(f"\n>>> Navegando: {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"  Timeout/error en goto: {e}")

    # Esperar un poco más para requests lentos
    await asyncio.sleep(3)

    # Intentar hacer scroll/click para triggear lazy loading
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
    except Exception:
        pass

    page.remove_listener("response", on_response)
    return responses


async def navigate_departamentos(page, base_section: str):
    """Intenta navegar por cada departamento para capturar datos regionales."""
    # Códigos de departamentos del Perú (ubigeo)
    departamentos = [
        "010000", "020000", "030000", "040000", "050000",
        "060000", "070000", "080000", "090000", "100000",
        "110000", "120000", "130000", "140000", "150000",
        "160000", "170000", "180000", "190000", "200000",
        "210000", "220000", "230000", "240000", "250000",
    ]

    responses = {}
    for ubigeo in departamentos:
        url = f"{BASE_URL}/main/detalle/{base_section}/{ubigeo}"
        resp = await capture_network(page, url, f"dep_{ubigeo}")
        responses.update(resp)

    return responses


async def main():
    print("=" * 60)
    print("SCRAPER ONPE 2026 - Iniciando")
    print("=" * 60)

    all_captured = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # 1. Navegar a la página principal primero para cargar la SPA
        print("\n[1/4] Cargando SPA principal...")
        resp = await capture_network(page, f"{BASE_URL}/main/resumen", "main")
        all_captured.update(resp)

        # 2. Navegar cada vista principal
        for tag, url in VIEWS.items():
            print(f"\n[Vista] {tag}")
            resp = await capture_network(page, url, tag)
            all_captured.update(resp)

        # 3. Intentar navegación por departamentos
        print("\n[3/4] Navegando departamentos - presidencial...")
        resp = await navigate_departamentos(page, "presidencial")
        all_captured.update(resp)

        print("\n[4/4] Navegando departamentos - senado-nacional...")
        resp = await navigate_departamentos(page, "senado-nacional")
        all_captured.update(resp)

        await browser.close()

    # Guardar todo lo capturado
    print(f"\n{'='*60}")
    print(f"Total de endpoints capturados: {len(all_captured)}")

    # Guardar el dump completo
    dump_path = DATA_DIR / "raw_capture.json"
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(all_captured, f, ensure_ascii=False, indent=2)
    print(f"Guardado: {dump_path}")

    # Mostrar las URLs encontradas
    print("\nEndpoints encontrados:")
    for url in sorted(all_captured.keys()):
        print(f"  {url}")

    # Intentar clasificar y guardar por categoría
    classify_and_save(all_captured)


def classify_and_save(data: dict):
    """Clasifica los datos capturados y los guarda por categoría."""
    presidencial = {}
    senado = {}
    otros = {}

    for url, body in data.items():
        url_lower = url.lower()
        if "presidencial" in url_lower or "presidente" in url_lower:
            presidencial[url] = body
        elif "senado" in url_lower or "senador" in url_lower:
            senado[url] = body
        else:
            otros[url] = body

    if presidencial:
        path = DATA_DIR / "presidencial.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(presidencial, f, ensure_ascii=False, indent=2)
        print(f"Presidencial ({len(presidencial)} endpoints): {path}")

    if senado:
        path = DATA_DIR / "senado.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(senado, f, ensure_ascii=False, indent=2)
        print(f"Senado ({len(senado)} endpoints): {path}")

    if otros:
        path = DATA_DIR / "otros.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(otros, f, ensure_ascii=False, indent=2)
        print(f"Otros ({len(otros)} endpoints): {path}")


if __name__ == "__main__":
    asyncio.run(main())
