import httpx, asyncio, re

headers_web = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
}
headers_api = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Referer': 'https://resultadoelectoral.onpe.gob.pe/main/resumen',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
    'Origin': 'https://resultadoelectoral.onpe.gob.pe',
}
BASE = 'https://resultadoelectoral.onpe.gob.pe/presentacion-backend'

async def main():
    async with httpx.AsyncClient(follow_redirects=True) as c:
        js_r = await c.get('https://resultadoelectoral.onpe.gob.pe/main-KINQGOLR.js', headers=headers_web, timeout=30)
        js = js_r.text

        # Find listarBase implementation
        for m in re.finditer(r'listarBase\([^)]*\)\s*\{.{300}', js):
            print(f'LISTAR_BASE IMPL: {m.group()[:300]}')
            print()
            break

        # Find what Il.getParticipantes or Il service does
        for m in re.finditer(r'Il\s*=\s*class.{500}', js):
            print(f'Il CLASS: {m.group()[:500]}')
            print()
            break

        # Find request interceptors - look for Authorization or token patterns
        for m in re.finditer(r'.{30}Authorization.{80}', js):
            print(f'AUTH: {m.group()[:150]}')

        # Find the urlServidor value
        for m in re.finditer(r'apiUrlLocal\s*[=:]\s*["\'][^"\']+["\']', js):
            print(f'API_URL: {m.group()[:100]}')
            break

        # Check actual response for a simple POST
        print('\n=== Testing POST resumen-general/totales with various bodies ===')

        # First get session from main page
        r_main = await c.get('https://resultadoelectoral.onpe.gob.pe/', headers=headers_web, timeout=15)
        print(f'Main page status: {r_main.status_code}')
        print(f'Cookies after main page: {dict(c.cookies)}')

        # Now test POST
        body = {'idAmbitoGeografico': 1, 'idEleccion': 10, 'tipoFiltro': 'ubigeo_nivel_01',
                'idUbigeoDepartamento': 20000, 'idUbigeoProvincia': None, 'idUbigeoDistrito': None}
        r = await c.post(f'{BASE}/resumen-general/totales', json=body, headers=headers_api, timeout=15)
        print(f'Status: {r.status_code}')
        print(f'Content-Type: {r.headers.get("content-type")}')
        print(f'Response (first 500): {r.text[:500]}')

asyncio.run(main())
