import csv, pathlib, logging

log = logging.getLogger("writer")
OUTFILE = pathlib.Path(__file__).parent.parent / "data" / "output" / "medicos_out.csv"

FIELDS = ["CRM","UF","Firstname","LastName","Medical specialty","Address A1","Complement A1","postal code A1","City A1","State A1","Phone A1","Phone A2","Cell phone A1","Cell phone A2","E-mail A1","E-mail A2","FullName"]

def write_header_once():
    if not OUTFILE.exists():
        with OUTFILE.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(FIELDS)

def append_row(row: dict):
    write_header_once()
    values = [row.get(f, "") for f in FIELDS]
    with OUTFILE.open("a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(values)
