import trafilatura, logging

log = logging.getLogger("clean")

def clean_html(html: str) -> str:
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    return text
