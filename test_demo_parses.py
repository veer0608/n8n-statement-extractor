"""
Prove the demo PDF is actually parseable by the workflow's logic.

This is a Python port of the two Code nodes in workflow.json (layout
normalisation + reconciliation), run against demo_statement.pdf. It exists so
the demo is verified before shipping - a sample file the product fails on is
worse than no sample at all.

Ground truth comes from make_demo_pdf.py, so this checks the parser against
what was actually printed, not against itself.
"""

import re
import sys
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import make_demo_pdf as demo

PDF = "demo_statement.pdf"

DATE_RE = re.compile(r"^\s*(\d{1,2}[/\-.](?:\d{1,2}|[A-Za-z]{3})[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})")
AMOUNT_RE = re.compile(r"\(?-?(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}\)?(?:\s*(?:CR|DR))?", re.I)

# Terminator rule - mirrors node 5. A summary line is not a continuation of the
# last transaction; without this the closing figure is swallowed into the final
# row's amount list.
# NOTE: \w* after "bal", not \b - a word boundary cannot match between "bal"
# and "ance", so \b here silently never fires on "CLOSING BALANCE".
TERMINATOR_RE = re.compile(
    r"^\s*(closing\s+bal\w*|balance\s+(c/f|carried\s+f\w*)|total\b|grand\s+total\b"
    r"|net\s+(movement|total)\b|summary\b)", re.I)
OPENING_RE = re.compile(
    r"^\s*(opening\s+bal\w*|balance\s+(b/f|brought\s+f\w*))", re.I)


def parse_amount(tok):
    neg = tok.strip().startswith("(") or re.search(r"DR\s*$", tok, re.I)
    n = re.sub(r"[(),\s]|CR|DR", "", tok, flags=re.I)
    try:
        v = float(n)
    except ValueError:
        return None
    return -abs(v) if neg else v


def amounts_in(line):
    return [a for a in (parse_amount(t) for t in AMOUNT_RE.findall(line)) if a is not None]


def extract_text():
    with pdfplumber.open(PDF) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def normalise(pages):
    """Port of node 5, including the terminator rule."""
    raw = [l.replace(" ", " ").rstrip() for l in "\n".join(pages).split("\n")]

    freq = {}
    for l in raw:
        k = l.strip()
        if len(k) > 3:
            freq[k] = freq.get(k, 0) + 1
    n_pages = len(pages)
    furniture = {
        k for k, n in freq.items()
        if n >= max(2, n_pages * 0.6) and not re.search(r"\d{2}[/\-.]\d{2}", k)
    }
    is_page_no = lambda l: re.match(r"^\s*(page\s*)?\d+\s*(of\s*\d+)?\s*$", l, re.I)

    lines = [l for l in raw if l.strip() and l.strip() not in furniture and not is_page_no(l)]

    rows, current = [], None
    printed_opening = printed_closing = None

    for line in lines:
        bare = line.strip()

        if OPENING_RE.match(bare) and not DATE_RE.match(bare):
            a = amounts_in(bare)
            if a:
                printed_opening = a[-1]
            continue

        if TERMINATOR_RE.match(bare) and not DATE_RE.match(bare):
            a = amounts_in(bare)
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

    out = []
    for i, r in enumerate(rows):
        flat = re.sub(r"\s{2,}", " ", " ".join([r["raw"]] + r["cont"])).strip()
        out.append({"rowIndex": i, "raw": flat, "amounts": amounts_in(flat),
                    "wrapped": bool(r["cont"])})

    statement = {"printedOpening": printed_opening, "printedClosing": printed_closing}
    return out, furniture, statement


def reconcile(rows, statement):
    """Port of node 7's balance walk. Convention: last amount on a row is the
    running balance."""
    prev = statement["printedOpening"]
    if prev is None:
        prev = demo.OPENING          # fallback, mirrors the form-field hint
    results = []
    for r in rows:
        if not r["amounts"]:
            results.append((r["rowIndex"], None, ["no_amounts"]))
            continue
        bal = r["amounts"][-1]
        movement = bal - prev
        flags = []
        others = [abs(a) for a in r["amounts"][:-1]]
        if not any(abs(abs(movement) - o) < 0.01 for o in others):
            flags.append("movement_not_found_in_row")
        prev = bal
        results.append((r["rowIndex"], bal, flags))
    return results, prev


def main():
    pages = extract_text()
    joined = "\n".join(pages)
    chars_per_page = len(re.sub(r"\s", "", joined)) / len(pages)
    print("pages extracted   : %d" % len(pages))
    print("chars/page        : %d  (triage route: %s)"
          % (chars_per_page, "digital" if chars_per_page >= 80 else "scanned"))

    print("\n--- the three deliberate cases present in the text layer ---")
    checks = {
        "CASE 1 wrapped desc (HARBOURSIDE cont. line)": "HARBOURSIDE SUPPLIES" in joined,
        "CASE 2 page-split cont. line on page 2": "CLEARVIEW ANALYTICS" in pages[1],
        "CASE 2 its amounts stayed on page 1": "58,900.00" in pages[0],
        "CASE 3 accounting parentheses (1,250.00)": "(1,250.00)" in joined,
    }
    for k, v in checks.items():
        print("  %-46s %s" % (k, "yes" if v else "NO"))

    rows, furniture, statement = normalise(pages)

    truth_closing = demo.OPENING + sum(
        (cr or 0) - (db or 0) for _d, _x, db, cr in demo.TXNS)

    print("\nfurniture removed : %d distinct repeated lines" % len(furniture))
    print("printed opening   : %s  (truth %.2f)"
          % (statement["printedOpening"], demo.OPENING))
    print("printed closing   : %s  (truth %.2f)"
          % (statement["printedClosing"], truth_closing))
    print("rows detected     : %d   (ground truth: %d)" % (len(rows), len(demo.TXNS)))

    wrapped = sum(1 for r in rows if r["wrapped"])
    truth_wrapped = sum(1 for _d, desc, _db, _cr in demo.TXNS if len(desc) > 1)
    print("wrapped rows      : %d   (ground truth: %d)" % (wrapped, truth_wrapped))

    results, closing = reconcile(rows, statement)
    bad = [(i, f) for i, _b, f in results if f]
    print("\nreconciled rows   : %d / %d" % (len(results) - len(bad), len(results)))
    print("closing (walked)  : %.2f" % closing)
    print("closing (truth)   : %.2f" % truth_closing)

    if bad:
        print("\nflagged rows:")
        for i, f in bad:
            print("  row %-3d %-32s %s" % (i, ",".join(f), rows[i]["raw"][:70]))

    conditions = {
        "row count matches": len(rows) == len(demo.TXNS),
        "wrapped count matches": wrapped == truth_wrapped,
        "walked closing matches truth": abs(closing - truth_closing) < 0.01,
        "printed opening captured": statement["printedOpening"] == demo.OPENING,
        "printed closing captured": statement["printedClosing"] is not None
                                    and abs(statement["printedClosing"] - truth_closing) < 0.01,
        "all rows reconcile": not bad,
        "all three cases present": all(checks.values()),
    }
    print("")
    for k, v in conditions.items():
        print("  %-30s %s" % (k, "pass" if v else "FAIL"))

    ok = all(conditions.values())
    print("\nRESULT: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
