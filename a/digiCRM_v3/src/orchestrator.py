
import asyncio, csv, pathlib, logging, argparse, re, aiohttp, requests, os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util

from .search import query_searx
from .fetch  import cached_fetch
from .clean  import clean_html
from .detect import detect_entities
from .classify import build_prompt, ask_llm
from .consolidate import consolidate
from .utils import normalize_state, map_specialties

# ───────── Config ─────────
INPUT  = pathlib.Path("data/input/medicos.csv")
OUTPUT = pathlib.Path("data/output/medicos_out.csv")

logging.basicConfig(filename="digicrm_v3.log",
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("orc")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cuda")

print("DEBUG: loading", INPUT, "size=", INPUT.stat().st_size)

def init_csv():
    if not OUTPUT.exists():
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text("CRM,UF,Firstname,LastName,Medical specialty,Address A1,Complement A1,postal code A1,City A1,State A1,Phone A1,Phone A2,Cell phone A1,Cell phone A2,E-mail A1,E-mail A2,FullName\n")

# ───────── Deep Harvest ─────────
async def deep_harvest(row, initial_urls, session):
    fullname = f"{row['Firstname']} {row['LastName']}".strip()
    extra = []
    href_re = re.compile(r'href=["\'](https?://[^"\']+)', re.I)
    for url in initial_urls:
        html,_ = await cached_fetch(url, session)
        if not html:
            continue
        for link in href_re.findall(html):
            if any(tok.lower() in link.lower() for tok in fullname.split()):
                extra.append(link)
        if len(extra)>=40:
            break
    # aggressive query
    q=f"{fullname} telefone email endereço"
    urls=await query_searx(q, max_results=20)
    extra.extend(urls)
    return extra[:60]

# ───────── enrich single medic ─────────
async def enrich_med(row, sem):
    fullname=f"{row['Firstname']} {row['LastName']}".strip()
    query=f"{fullname} CRM {row['CRM']} {row['UF']}"
    urls=await query_searx(query, max_results=30)
    results=[]
    async with aiohttp.ClientSession() as sess:
        pbar=tqdm(total=len(urls), desc=row['CRM'], leave=False)
        for url in urls:
            html,_=await cached_fetch(url,sess)
            pbar.update(1)
            if not html: continue
            text=clean_html(html)
            if not text: continue
            sentences=re.split(r"[\n\.]", text)[:120]
            if not sentences: continue
            emb_sent=model.encode(sentences, convert_to_tensor=True)
            emb_q=model.encode(fullname, convert_to_tensor=True)
            idx=int(util.pytorch_cos_sim(emb_q, emb_sent)[0].argmax())
            chunk=" ".join(sentences[max(0,idx-2):idx+3])
            hints=detect_entities(chunk)
            prompt=build_prompt({"full_name":fullname,"crm":row["CRM"],"uf":row["UF"]}, chunk)
            llm=ask_llm(prompt) or {}
            if isinstance(llm, list):
                llm=llm[0] if llm else {}
            for i,v in enumerate(hints.get("phones",[])[:2],1):
                llm[f"phone{i}"]=v
            for i,v in enumerate(hints.get("emails",[])[:2],1):
                llm[f"email{i}"]=v
            if hints.get("ceps"):
                llm["postal_code"]=hints["ceps"][0]
            results.append(llm)
            if llm.get("email1") and llm.get("phone1"):
                break
        pbar.close()

        merged=consolidate(results, fullname)

        # address enrichment via ViaCEP
        if merged.get("postal_code") and (not merged.get("city") or not merged.get("address")):
            cep=re.sub(r"[^0-9]", "", merged["postal_code"])
            try:
                r=requests.get(f"https://viacep.com.br/ws/{cep}/json/")
                if r.ok and "erro" not in r.text:
                    data=r.json()
                    merged.setdefault("address", data.get("logradouro",""))
                    merged.setdefault("city", data.get("localidade",""))
                    merged.setdefault("state", data.get("uf",""))
            except Exception as e:
                log.warning("ViaCEP %s", e)

        # aggressive pass if still missing critical
        if not (merged.get("email1") and merged.get("phone1")):
            deep_urls=await deep_harvest(row, urls, sess)
            for durl in deep_urls:
                html,_=await cached_fetch(durl,sess)
                if not html: continue
                hints=detect_entities(clean_html(html))
                extra={}
                for i,v in enumerate(hints.get("phones",[])[:2],1):
                    extra[f"phone{i}"]=v
                for i,v in enumerate(hints.get("emails",[])[:2],1):
                    extra[f"email{i}"]=v
                if hints.get("ceps"):
                    extra["postal_code"]=hints["ceps"][0]
                if extra:
                    results.append(extra)
            merged=consolidate(results, fullname)

    # normalize outputs
    specialty=map_specialties(merged.get("specialty",""))
    address = merged.get("address","").replace(",", ";")
    city    = merged.get("city","")
    state   = normalize_state(merged.get("state", row["UF"])).replace(",", " ")
    row_out=[
        row["CRM"], row["UF"], row["Firstname"], row["LastName"],
        specialty,
        address,
        merged.get("complement","").replace(",",";"),
        merged.get("postal_code",""),
        city,
        state,
        merged.get("phone1",""),
        merged.get("phone2",""),
        "", "", merged.get("email1",""), merged.get("email2",""),
        fullname
    ]
    with OUTPUT.open("a") as f:
        f.write(",".join(v if v else "" for v in row_out)+"\n")
    sem.release()

# ───────── Main ─────────
async def main(batch:int, workers:int):
    init_csv()
    sem=asyncio.Semaphore(workers)
    tasks=[]
    with INPUT.open() as f:
        reader=csv.DictReader(f)
        print("DEBUG: DictReader fieldnames ->", reader.fieldnames)
        for i,row in enumerate(reader):
            if i>=batch: break
            await sem.acquire()
            tasks.append(asyncio.create_task(enrich_med(row, sem)))
    await asyncio.gather(*tasks)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("batch", type=int)
    parser.add_argument("workers", type=int)
    args=parser.parse_args()
    asyncio.run(main(args.batch, args.workers))
