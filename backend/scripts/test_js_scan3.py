import httpx, asyncio, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
}

async def main():
    async with httpx.AsyncClient(follow_redirects=True) as c:
        rs = await c.get('https://resultadoelectoral.onpe.gob.pe/main-KINQGOLR.js', headers=headers, timeout=30)
        js = rs.text

        # Find lu.departments URL
        for m in re.finditer(r'lu\s*=\s*\{[^}]{1,500}departments[^}]{1,500}\}', js):
            print(f'lu OBJECT: {m.group()[:400]}')
            print()

        # Find Xh.departments URL
        for m in re.finditer(r'Xh\s*=\s*\{[^}]{1,500}departments[^}]{1,500}\}', js):
            print(f'Xh OBJECT: {m.group()[:400]}')
            print()

        # Search for "departamentos" endpoint
        for m in re.finditer(r'.{30}departamentos.{80}', js):
            if 'http' in m.group() or 'apiUrl' in m.group() or 'urlServidor' in m.group():
                print(f'DEPTS_EP: {m.group()[:150]}')

        # Find what POST body is actually used for participantes presidencial
        # Look for context around "presidencial" + "post"
        for m in re.finditer(r'.{50}eleccion-presidencial.{150}', js):
            ctx = m.group()
            if 'post' in ctx.lower() or 'Post' in ctx:
                print(f'PRES_POST: {ctx[:200]}')
                print()

        # Look for the tipoFiltro function - Qi(t)
        for m in re.finditer(r'Qi\s*=?\s*function.{200}', js):
            print(f'Qi FUNC: {m.group()[:200]}')
        for m in re.finditer(r'function Qi.{200}', js):
            print(f'Qi FUNC2: {m.group()[:200]}')
        for m in re.finditer(r'Qi\(.{0,5}\)\s*\{.{200}', js):
            print(f'Qi ARROW: {m.group()[:200]}')

        # Find listarBase function used for presidencial
        for m in re.finditer(r'listarBase.{0,5}\(t,.{0,5}"participantes-ubicacion-geografica-nombre"\).{200}', js):
            print(f'LISTAR_BASE: {m.group()[:200]}')

asyncio.run(main())
