"""
Scan a tree of PDFs for statement-like structure.

Prints filenames and shape metrics ONLY - never transaction text, names, or
account numbers. The goal is to find a testable statement, not to read anything.
"""
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pdfplumber

ROOTS = sys.argv[1:] or [os.path.expanduser("~/Downloads")]  # pass dirs to scan
DATE_RE = re.compile(r"^\s*(\d{1,2}[/\-.](?:\d{1,2}|[A-Za-z]{3})[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})")
AMOUNT_RE = re.compile(r"\(?-?(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}\)?", re.I)
MARKERS = re.compile(
    r"\b(statement of account|account statement|opening balance|closing balance|"
    r"balance b/f|balance c/f|withdrawal|deposit|narration|value date|"
    r"transaction date|available balance)\b", re.I)

paths = []
for root in ROOTS:
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".pdf"):
                paths.append(os.path.join(dirpath, f))

print("scanning %d PDFs...\n" % len(paths))

encrypted = 0
hits = []
for p in paths:
    try:
        with pdfplumber.open(p) as pdf:
            n_pages = len(pdf.pages)
            text = "\n".join((pg.extract_text() or "") for pg in pdf.pages[:6])
    except Exception as e:
        if "Password" in type(e).__name__:
            encrypted += 1
        continue

    marks = len(MARKERS.findall(text))
    lines = [l for l in text.split("\n") if l.strip()]
    dated = [l for l in lines if DATE_RE.match(l) and AMOUNT_RE.search(l)]
    if marks >= 2 and len(dated) >= 5:
        three_plus = sum(1 for l in dated if len(AMOUNT_RE.findall(l)) >= 3)
        hits.append((len(dated), three_plus, marks, n_pages, p))

print("encrypted / unreadable: %d" % encrypted)
print("statement-like PDFs   : %d\n" % len(hits))

for dated, three_plus, marks, n_pages, p in sorted(hits, reverse=True):
    print("%-58s pages=%-3d dated_rows=%-4d rows_with_3+_amounts=%-4d markers=%d"
          % (os.path.basename(p)[:58], n_pages, dated, three_plus, marks))
    print("    %s" % p)
    print("    balance column likely: %s" % ("YES" if three_plus >= dated * 0.5 else "no"))
