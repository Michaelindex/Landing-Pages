
import re, collections
from .utils import normalize_phone, normalize_email, email_probability, map_specialties

PRIORITY_ORDER = [
    "email1","email2","phone1","phone2","postal_code",
    "address","city","state","specialty","complement"
]

def consolidate(results:list[dict], full_name:str)->dict:
    merged={}
    # choose best email/phone based on probability/validity
    emails=[]
    phones=[]
    for res in results:
        e1=res.get("email1")
        if e1: emails.append(e1)
        e2=res.get("email2")
        if e2: emails.append(e2)
        p1=res.get("phone1")
        if p1: phones.append(p1)
        p2=res.get("phone2")
        if p2: phones.append(p2)
    if emails:
        scored=sorted([(email_probability(e,full_name),e) for e in emails], reverse=True)
        merged["email1"]=normalize_email(scored[0][1])
        if len(scored)>1:
            merged["email2"]=normalize_email(scored[1][1])
    if phones:
        uniq=[]
        for p in phones:
            np=normalize_phone(p)
            if np and np not in uniq:
                uniq.append(np)
        if uniq:
            merged["phone1"]=uniq[0]
            if len(uniq)>1:
                merged["phone2"]=uniq[1]
    # merge rest giving precedence earlier in list
    for key in PRIORITY_ORDER:
        for res in results:
            v=res.get(key)
            if v and key not in merged:
                merged[key]=v
    # map specialty to area
    if "specialty" in merged:
        merged["specialty"]=map_specialties(merged["specialty"])
    return merged
