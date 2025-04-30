
import re, phonenumbers

# Regular expressions
CEP_RE    = re.compile(r"\b\d{5}-?\d{3}\b")
EMAIL_RE  = re.compile(r"[\w\.-]+@[\w\.-]+", re.I)
PHONE_RE  = re.compile(r"(?:\+\d{1,3})?\d{10,13}")

UF_TO_STATE = {
    "AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará","DF":"Distrito Federal",
    "ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais",
    "PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte",
    "RS":"Rio Grande do Sul","RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SP":"São Paulo","SE":"Sergipe","TO":"Tocantins"
}

SPECIALTY_TO_AREA = {
    "pediatria":"Pediatria",
    "pediatra":"Pediatria",
    "cardiologia":"Medicina interna",
    "cardiologista":"Medicina interna",
    "alergia":"Imunologia",
    "imunologia":"Imunologia",
    "ortopedia":"Cirurgia",
    "traumatologia":"Cirurgia",
    "radiologia":"Diagnóstico",
    "ginecologia":"Saúde da mulher",
    "homeopatia":"Medicina alternativa",
    "nutrologia":"Nutrição",
    # add more as needed
}

def normalize_state(uf:str)->str:
    return UF_TO_STATE.get(uf.upper(), uf)

def normalize_phone(p:str)->str|None:
    if p is None: return None
    if isinstance(p,(int,float)):
        p=str(int(p))
    p=re.sub(r"[^0-9+]", "", p)
    if len(p)<10: return None
    try:
        n=phonenumbers.parse(p, "BR")
        if not phonenumbers.is_valid_number(n):
            return None
        return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        return None

def normalize_email(e:str)->str|None:
    if not e: return None
    e=e.strip()
    if "," in e:
        parts=[x.strip() for x in e.split(",") if x.strip()]
        return parts[0] if parts else None
    return e

def email_probability(email:str, fullname:str)->float:
    """ crude heuristic """
    email=email.lower()
    tokens=[t.lower() for t in fullname.split()]
    score=sum(1 for t in tokens if t[:5] in email)/len(tokens)
    return score

def map_specialties(spec_str:str)->str:
    if not spec_str:
        return ""
    specs=[s.strip() for s in re.split(r"[;/|]", spec_str) if s.strip()]
    areas=set()
    for s in specs:
        key=s.lower()
        for k,v in SPECIALTY_TO_AREA.items():
            if k in key:
                areas.add(v)
    area_part=" ".join(sorted(areas))
    spec_part=" ".join(specs)
    if area_part:
        return f"{area_part} - {spec_part}"
    return spec_part
