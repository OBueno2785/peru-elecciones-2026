import httpx, asyncio, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
    'Accept': 'text/html,*/*',
}

async def main():
    async with httpx.AsyncClient(follow_redirects=True) as c:
        r = await c.get('https://resultadoelectoral.onpe.gob.pe/', headers=headers, timeout=20)
        html = r.text

        scripts = re.findall(r'src="([^"]*\.js[^"]*?)"', html)
        print(f'Found {len(scripts)} script tags')
        for s in scripts[:10]:
            print(f'  {s}')

        main_bundles = [s for s in scripts if 'main' in s or 'chunk' in s or 'app' in s]
        print(f'App-like bundles: {main_bundles[:5]}')

        for script_url in main_bundles[:3]:
            if not script_url.startswith('http'):
                script_url = 'https://resultadoelectoral.onpe.gob.pe' + ('/' if not script_url.startswith('/') else '') + script_url
            try:
                rs = await c.get(script_url, headers=headers, timeout=30)
                js = rs.text
                print(f'\n=== {script_url[-60:]} ({len(js)} chars) ===')
                # Search for API endpoint patterns
                matches = re.findall(r'["\']([^"\']*presentacion-backend[^"\']+)["\']', js)
                for m in matches[:20]:
                    print(f'  {m}')
                # Search for tipoFiltro
                for m in re.findall(r'.{60}tipoFiltro.{60}', js)[:5]:
                    print(f'  FILTRO: {m}')
                # Search for ambito_geografico
                for m in re.findall(r'.{40}ambito_geografico.{40}', js)[:5]:
                    print(f'  AMBITO: {m}')
                # Search for idAmbitoGeografico
                for m in re.findall(r'.{40}idAmbitoGeografico.{40}', js)[:5]:
                    print(f'  ID_AMBITO: {m}')
            except Exception as e:
                print(f'  Error: {e}')

asyncio.run(main())
