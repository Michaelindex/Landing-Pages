# ───────────────────────────── src/search.py ─────────────────────────────
"""
Camada de busca no SearXNG interno (https://search.piattino.com.br).

Função pública: query_searx(query: str,
                            *,
                            max_results: int = 30,
                            aggressive: bool = False) -> list[str]

• max_results   → total que você quer de volta (deduplicado)
• aggressive    → False = só a primeira página
                  True  = percorre mais páginas até encher max_results
"""

import aiohttp, asyncio, urllib.parse, logging

SEARX_BASE   = "https://search.piattino.com.br"
HEADERS      = {"User-Agent": "Mozilla/5.0 DigiCRM/2.21"}
MAX_PAGES    = 10        # segurança para não varrer infinito
log = logging.getLogger("search")


async def _fetch_page(session: aiohttp.ClientSession, q: str, page: int = 1):
    """Baixa uma página JSON do SearXNG (já com &format=json)."""
    url = (
        f"{SEARX_BASE}/search"
        f"?q={urllib.parse.quote_plus(q)}"
        f"&format=json&pageno={page}"
    )
    try:
        async with session.get(url, headers=HEADERS, timeout=30) as resp:
            if resp.status == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                data = await resp.json()
                return data.get("results", [])
            else:
                log.warning("SearX status %s para %s", resp.status, url)
    except Exception as e:
        log.warning("SearX erro %s para %s", e, url)
    return []


async def query_searx(query: str, *, max_results: int = 30, aggressive: bool = False) -> list[str]:
    """
    Retorna até `max_results` URLs (deduplicadas).
    Quando aggressive=True vai folheando páginas adicionais.
    """
    collected: list[str] = []
    seen: set[str] = set()

    async with aiohttp.ClientSession() as sess:
        page = 1
        while len(collected) < max_results:
            if page > MAX_PAGES:    # trava de segurança
                break

            results = await _fetch_page(sess, query, page)
            if not results:         # nada mais a folhear
                break

            for r in results:
                url = r.get("url")
                if url and url not in seen:
                    collected.append(url)
                    seen.add(url)
                    if len(collected) >= max_results:
                        break

            # Página única? então sai se não for agressivo
            if not aggressive:
                break
            page += 1
            await asyncio.sleep(0.8)   # não martelar o servidor

    return collected[:max_results]
# ─────────────────────────────────────────────────────────────────────────
