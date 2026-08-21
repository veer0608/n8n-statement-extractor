"""
Run node 5 (layout normalisation) against a real statement and report how well
extraction worked - WITHOUT printing the transaction contents.

This is the user's real card data in a persistent transcript, so descriptions
and amounts are masked. Only structural pass/fail metrics are printed, plus a
few rows shown as shape skeletons (digit->#, letter->x) to prove the parse
without revealing the data.
"""
import re
import sys

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATH = sys.argv[1]

DATE_RE = re.compile(r"^\s*(\d{1,2}[/\-.](?:\d{1,2}|[A-Za-z]{3})[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})")
AMOUNT_RE = re.compile(r"\(?-?(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}\)?(?:\s*(?:CR|DR))?", re.I)
TERMINATOR_RE = re.compile(
    r"^\s*(closing\s+bal\w*|balance\s+(c/f|carried\s+f\w*)|total\b|grand\s+total\b"
    r"|net\s+(movement|total)\b|summary\b)", re.I)
OPENING_RE = re.compile(r"^\s*(opening\s+bal\w*|balance\s+(b/f|brought\s+f\w*))", re.I)


def parse_amount(tok):
    neg = tok.strip().startswith("(") or re.search(r"DR\s*$", tok, re.I)
    n = re.sub(r"[(),\s]|CR|DR", "", tok, flags=re.I)
    try:
        v = float(n)
    except ValueError:
        return None
    return -abs(v) if neg else v


def to_iso(s, order):
    if not s:
        return None
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", s)
    if m:
        d = m.group(2) if order == "MDY" else m.group(1)
        mo = m.group(1) if order == "MDY" else m.group(2)
        y = ("20" + m.group(3)) if len(m.group(3)) == 2 else m.group(3)
        if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return "%s-%02d-%02d" % (y, int(mo), int(d))
    m = re.match(r"^(\d{1,2})[/\-.]([A-Za-z]{3})[/\-.](\d{2,4})$", s)
    if m:
        months = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6, jul=7,
                      aug=8, sep=9, oct=10, nov=11, dec=12)
        mo = months.get(m.group(2).lower())
        if mo:
            y = ("20" + m.group(3)) if len(m.group(3)) == 2 else m.group(3)
            return "%s-%02d-%02d" % (y, mo, int(m.group(1)))
    return None


def skeleton(s):
    return re.sub(r"[A-Za-z]", "x", re.sub(r"\d", "#", s))[:52]


with pdfplumber.open(PATH) as pdf:
    pages = [p.extract_text() or "" for p in pdf.pages]

raw = [l.replace(" ", " ").rstrip() for l in "\n".join(pages).split("\n")]

# furniture removal
freq = {}
for l in raw:
    k = l.strip()
    if len(k) > 3:
        freq[k] = freq.get(k, 0) + 1
n_pages = len(pages)
furniture = {k for k, n in freq.items()
             if n >= max(2, n_pages * 0.6) and not re.search(r"\d{2}[/\-.]\d{2}", k)}
is_page_no = lambda l: re.match(r"^\s*(page\s*)?\d+\s*(of\s*\d+)?\s*$", l, re.I)
lines = [l for l in raw if l.strip() and l.strip() not in furniture and not is_page_no(l)]

# date order
day_first = month_first = 0
for l in lines:
    m = re.match(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.]\d{2,4}", l)
    if m:
        if int(m.group(1)) > 12:
            day_first += 1
        if int(m.group(2)) > 12:
            month_first += 1
order = "DMY"
if month_first and not day_first:
    order = "MDY"
confident = bool(day_first) ^ bool(month_first)

# row assembly with terminator rule
rows, current = [], None
printed_opening = printed_closing = None
for line in lines:
    bare = line.strip()
    if OPENING_RE.match(bare) and not DATE_RE.match(bare):
        a = [x for x in (parse_amount(t) for t in AMOUNT_RE.findall(bare)) if x is not None]
        if a:
            printed_opening = a[-1]
        continue
    if TERMINATOR_RE.match(bare) and not DATE_RE.match(bare):
        a = [x for x in (parse_amount(t) for t in AMOUNT_RE.findall(bare)) if x is not None]
        if a:
            printed_closing = a[-1]
        if current:
            rows.append(current)
            current = None
        continue
    if DATE_RE.match(line):
        if current:
            rows.append(current)
        current = {"raw": line, "cont": []}
    elif current:
        current["cont"].append(bare)
if current:
    rows.append(current)

# field extraction
parsed = []
for r in rows:
    flat = re.sub(r"\s{2,}", " ", " ".join([r["raw"]] + r["cont"])).strip()
    toks = AMOUNT_RE.findall(flat)
    amounts = [x for x in (parse_amount(t) for t in toks) if x is not None]
    date_str = (DATE_RE.match(flat).group(0).strip() if DATE_RE.match(flat) else "")
    parsed.append({
        "iso": to_iso(date_str, order),
        "n_amounts": len(amounts),
        "wrapped": bool(r["cont"]),
        "flat": flat,
    })

n = len(parsed)
dates_ok = sum(1 for p in parsed if p["iso"])
have_amount = sum(1 for p in parsed if p["n_amounts"] >= 1)
wrapped = sum(1 for p in parsed if p["wrapped"])
amt_dist = {}
for p in parsed:
    amt_dist[p["n_amounts"]] = amt_dist.get(p["n_amounts"], 0) + 1

print("=== REAL STATEMENT EXTRACTION (contents masked) ===")
print("pages                    : %d" % n_pages)
print("furniture lines removed  : %d" % len(furniture))
print("date order               : %s (%s)"
      % (order, "confident" if confident else "assumed - all days <= 12"))
print("rows detected            : %d" % n)
print("dates resolved to ISO    : %d / %d  (%.0f%%)" % (dates_ok, n, 100 * dates_ok / n if n else 0))
print("rows with >=1 amount     : %d / %d  (%.0f%%)" % (have_amount, n, 100 * have_amount / n if n else 0))
print("amounts-per-row spread   : %s" % dict(sorted(amt_dist.items())))
print("wrapped rows stitched    : %d" % wrapped)
print("printed opening captured : %s" % (printed_opening is not None))
print("printed closing captured : %s" % (printed_closing is not None))

failed = [p for p in parsed if not p["iso"] or p["n_amounts"] < 1]
print("\nrows that FAILED extraction: %d" % len(failed))
for p in failed[:8]:
    print("   skeleton: %s" % skeleton(p["flat"]))

print("\nsample of SUCCESSFUL rows (shape only, data masked):")
for p in [x for x in parsed if x["iso"] and x["n_amounts"]][:5]:
    print("   %s  amounts=%d  %s" % (p["iso"], p["n_amounts"], skeleton(p["flat"])))
