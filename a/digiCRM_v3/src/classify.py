
import httpx, yaml, pathlib, logging, json, re

log = logging.getLogger("classify")
cfg = yaml.safe_load((pathlib.Path(__file__).parent.parent/'config'/'model_local.yml').read_text())
ENDPOINT = cfg['host'].rstrip('/') + cfg['endpoint']

def build_prompt(ctx: dict, chunk: str) -> str:
    return f"""Nome: {ctx['full_name']}
CRM: {ctx['crm']}  UF: {ctx['uf']}
### Texto
{chunk}
### Tarefa
Retorne SOMENTE o objeto JSON com as chaves:
specialty,address,complement,postal_code,city,state,
phone1,phone2,cell1,cell2,email1,email2.
Sem markdown, sem explicação."""

def _extract_json(txt: str):
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

def ask_llm(prompt: str):
    payload = cfg['default_kwargs'] | {'model': cfg['model'], 'prompt': prompt}
    try:
        r = httpx.post(ENDPOINT, json=payload, timeout=180)
        r.raise_for_status()
    except Exception as e:
        log.warning('LLM HTTP error %s', e)
        return None
    body = r.text
    if body.lstrip().startswith('{'):
        try:
            body_json = json.loads(body)
            txt = body_json.get('response','')
        except json.JSONDecodeError:
            txt = None
    else:
        txt = None
    if not txt:
        # NDJSON fallback
        for line in reversed([l.strip() for l in body.splitlines() if l.strip()]):
            try:
                obj = json.loads(line)
                if 'response' in obj:
                    txt = obj['response']
                    break
            except json.JSONDecodeError:
                continue
    if not txt:
        return None
    return _extract_json(txt)
