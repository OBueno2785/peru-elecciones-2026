import httpx, asyncio, re, json

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
        rs = await c.get('https://resultadoelectoral.onpe.gob.pe/main-KINQGOLR.js', headers=headers_web, timeout=30)
        js = rs.text

        # Full Qi function
        for m in re.finditer(r'function Qi\([^)]*\)\s*\{.{400}', js):
            print(f'Qi FULL: {m.group()[:400]}')
            print()
            break

        # Je constants (find the LEVEL_01 etc.)
        for m in re.finditer(r'Je\s*=\s*\{[^}]{1,400}\}', js):
            print(f'Je CONSTANTS: {m.group()[:400]}')
            print()
            break

        # Find listarParticipantes usage for presidencial tab
        for m in re.finditer(r'.{30}listarParticipantes.{200}', js):
            ctx = m.group()
            if 'presidencial' in ctx.lower() or 'eleccion' in ctx.lower():
                print(f'LISTAR_PRES: {ctx[:250]}')
                print()

        # Now call the departments endpoint
        print('=== Calling ubigeos/departamentos POST ===')
        r = await c.post(f'{BASE}/ubigeos/departamentos',
                         json={'idEleccion': 10, 'idAmbitoGeografico': 1},
                         headers=headers_api, timeout=10)
        data = r.json() if 'json' in r.headers.get('content-type','') else {}
        print(f'success={data.get("success")} records={len(data.get("data", []))}')
        if data.get('data'):
            for d in data['data'][:5]:
                print(f'  {json.dumps(d, ensure_ascii=False)}')

asyncio.run(main())
