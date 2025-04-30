
import re, itertools
from .utils import CEP_RE, EMAIL_RE, PHONE_RE

def detect_entities(text:str)->dict:
    phones=re.findall(PHONE_RE,text)
    emails=re.findall(EMAIL_RE,text)
    ceps=re.findall(CEP_RE,text)
    # dedupe keeping order
    uniq=lambda seq:list(dict.fromkeys(seq))
    return {
        "phones":uniq(phones),
        "emails":uniq(emails),
        "ceps":uniq(ceps)
    }
