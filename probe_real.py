"""
Structural probe of a real statement PDF. Deliberately prints NO transaction
detail, no names, no account numbers - only shape metrics, so a sensitive
document can be assessed without its contents landing in a transcript.
"""
import re
import sys

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATH = sys.argv[1]

DATE_RE = re.compile(r"^\s*(\d{1,2}[/\-.](?:\d{1,2}|[A-Za-z]{3})[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})")
AMOUNT_RE = re.compile(r"\(?-?(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}\)?(?:\s*(?:CR|DR))?", re.I)

try:
    pdf = pdfplumber.open(PATH)
except Exception as e:
    print("CANNOT OPEN:", type(e).__name__, str(e)[:120])
    print("(encrypted statements need the password - common for Indian card statements)")
    sys.exit(1)

pages = [p.extract_text() or "" for p in pdf.pages]
pdf.close()

joined = "\n".join(pages)
lines = [l for l in joined.split("\n") if l.strip()]
chars_per_page = len(re.sub(r"\s", "", joined)) / max(1, len(pages))

dated = [l for l in lines if DATE_RE.match(l)]
with_amounts = [l for l in dated if AMOUNT_RE.search(l)]
amt_counts = [len(AMOUNT_RE.findall(l)) for l in with_amounts]

print("pages              : %d" % len(pages))
print("chars/page         : %d  -> triage: %s"
      % (chars_per_page, "digital" if chars_per_page >= 80 else "SCANNED (needs OCR)"))
print("non-empty lines    : %d" % len(lines))
print("date-prefixed lines: %d" % len(dated))
print("  ...with amounts  : %d" % len(with_amounts))

if amt_counts:
    from collections import Counter
    print("amounts per row    : %s" % dict(sorted(Counter(amt_counts).items())))
    print("  3+ amounts/row suggests a running-balance column is present")
    print("  2 amounts/row usually means NO balance column (card statements)")

has_balance_word = bool(re.search(r"\b(closing|opening)\s+bal", joined, re.I))
print("opening/closing balance line present: %s" % has_balance_word)

wrapped_guess = len([l for l in lines if not DATE_RE.match(l)]) - (len(lines) - len(dated))
print("date order detectable: ", end="")
day_first = month_first = 0
for l in dated:
    m = re.match(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.]\d{2,4}", l)
    if m:
        if int(m.group(1)) > 12:
            day_first += 1
        if int(m.group(2)) > 12:
            month_first += 1
if day_first and not month_first:
    print("DMY (confident)")
elif month_first and not day_first:
    print("MDY (confident)")
elif day_first and month_first:
    print("CONFLICT")
else:
    print("ambiguous (every day <= 12)")
