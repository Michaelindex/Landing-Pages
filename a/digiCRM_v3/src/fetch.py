import aiohttp, asyncio, logging, hashlib, pathlib, yaml, datetime
from tqdm.asyncio import tqdm_asyncio

log = logging.getLogger("fetch")
HEADERS = {"User-Agent": "Mozilla/5.0 DigiCRM/1.0"}

CACHE_DIR = pathlib.Path(__file__).parent.parent / "data" / "cache" / "html"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

async def fetch_html(url: str, session: aiohttp.ClientSession, retries: int = 3, timeout: int = 20) -> tuple[str | None, str | None]:
    last_err = None
    for _ in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=timeout) as resp:
                if resp.status == 200 and "text/html" in resp.headers.get("content-type",""):
                    raw = await resp.text(errors="ignore")
                    return raw, None
                last_err = f"HTTP {resp.status}"
        except Exception as e:
            last_err = str(e)
        await asyncio.sleep(1)
    return None, last_err

async def cached_fetch(url: str, session: aiohttp.ClientSession) -> tuple[str | None, str | None]:
    h = hashlib.sha256(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{h}.html"
    if cache_file.exists():
        log.debug("cache hit %s", url)
        return cache_file.read_text(encoding="utf-8", errors="ignore"), None
    html, err = await fetch_html(url, session)
    if html:
        cache_file.write_text(html, encoding="utf-8", errors="ignore")
    return html, err
