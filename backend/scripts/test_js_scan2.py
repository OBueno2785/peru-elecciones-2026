import httpx, asyncio, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
}

async def main():
    async with httpx.AsyncClient(follow_redirects=True) as c:
        rs = await c.get('https://resultadoelectoral.onpe.gob.pe/main-KINQGOLR.js', headers=headers, timeout=30)
        js = rs.text
        print(f'JS size: {len(js)} chars')

        # Find idUbigeoDepartamento usage context
        for m in re.finditer(r'.{100}idUbigeoDepartamento.{100}', js):
            print(f'UBIGEO_DEP: {m.group()}')
            print()

        # Find getParticipantes or participantes endpoint
        for m in re.finditer(r'.{80}participantes.{80}', js):
            print(f'PARTICIPANTES: {m.group()}')
            print()

        # Find the exact URL pattern for presidencial with department
        for m in re.finditer(r'.{60}eleccion-presidencial.{60}', js):
            print(f'PRESIDENCIAL: {m.group()}')
            print()

        # Find Qn constant value
        for m in re.finditer(r'Qn\s*[=:]\s*(\d+)', js):
            print(f'Qn VALUE: {m.group()}')

        # Find getDepartments implementation
        for m in re.finditer(r'getDepartments\$.{200}', js):
            print(f'GET_DEPTS: {m.group()[:200]}')
            print()

asyncio.run(main())
