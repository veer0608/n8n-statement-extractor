"""
Second demo statement - a deliberately DIFFERENT layout from demo_statement.pdf,
to show the workflow isn't tuned to one PDF.

Different on the axes that actually exercise the code:
  - EU comma-decimal amounts: 1.234,56  (tests the decimal-separator inference)
  - DD-MMM-YYYY dates: 02-Jun-2026       (tests the month-name date path)
  - BALANCE B/F / BALANCE C/F labels      (tests the alternate opening/closing
                                           markers, not OPENING/CLOSING BALANCE)
  - Withdrawal / Deposit columns, a EUR account, different bank and furniture
  - a wrapped narrative

Fictional. Ledger is arithmetically exact: B/F + movements == C/F.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = "demo_statement_2.pdf"

BANK = "Sterling Union Bank"
ACCOUNT = "Halcyon Freight GmbH"
IBAN = "DE44 5001 0517 0000 9931 20"
PERIOD = "01 Jun 2026 - 30 Jun 2026 (EUR)"
OPENING = 52_480.00

# (date, narrative_lines, withdrawal, deposit)
TXNS = [
    ("02-Jun-2026", ["SEPA CREDIT  ORION LOGISTIK GMBH"], None, 18_750.00),
    ("04-Jun-2026", ["CARD PURCHASE 4471  FUELSTATION GMBH"], 1_284.50, None),
    ("06-Jun-2026", ["SEPA DEBIT  QUARTERLY LEASE - HARBOURSIDE",
                     "SUPPLIES LLP  INV 2026/Q2/0771"], 9_900.00, None),  # wrapped
    ("09-Jun-2026", ["SALARY RUN JUN 2026"], 21_300.00, None),
    ("11-Jun-2026", ["SEPA CREDIT  KESTREL INDUSTRIES"], None, 33_000.00),
    ("14-Jun-2026", ["ACCOUNT FEE - MONTHLY"], 42.00, None),
    ("17-Jun-2026", ["SEPA CREDIT  MERIDIAN PARTNERS"], None, 7_615.25),
    ("20-Jun-2026", ["VAT PAYMENT Q2 2026"], 12_845.75, None),
    ("23-Jun-2026", ["CARD PURCHASE 4471  OFFICE SUPPLIES"], 613.40, None),
    ("26-Jun-2026", ["SEPA CREDIT  ATLAS SHIPPING"], None, 24_900.00),
    ("28-Jun-2026", ["ATM WITHDRAWAL - FRANKFURT HBF"], 500.00, None),
    ("30-Jun-2026", ["INTEREST CREDITED"], None, 128.60),
]
PAGE_BREAK_AFTER = 6  # rows 0..6 on page 1, rest on page 2

LEFT = 18 * mm
RIGHT = A4[0] - 18 * mm
COL_DATE = LEFT
COL_DESC = LEFT + 26 * mm
COL_WD = LEFT + 108 * mm
COL_DEP = LEFT + 138 * mm
COL_BAL = RIGHT


def money(v):
    """EU format: 1.234,56 - thousands dot, decimal comma."""
    s = "{:,.2f}".format(v)              # 1,234.56
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def header(c):
    c.setFont("Helvetica-Bold", 13)
    c.drawString(LEFT, A4[1] - 20 * mm, BANK)
    c.setFont("Helvetica", 8)
    c.drawString(LEFT, A4[1] - 25 * mm, "Account Statement")
    c.drawRightString(RIGHT, A4[1] - 20 * mm, "IBAN: %s" % IBAN)
    c.drawRightString(RIGHT, A4[1] - 25 * mm, PERIOD)
    c.line(LEFT, A4[1] - 28 * mm, RIGHT, A4[1] - 28 * mm)
    y = A4[1] - 34 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DATE, y, "Value Date")
    c.drawString(COL_DESC, y, "Narrative")
    c.drawRightString(COL_WD, y, "Withdrawal")
    c.drawRightString(COL_DEP, y, "Deposit")
    c.drawRightString(COL_BAL, y, "Balance")
    c.line(LEFT, y - 2 * mm, RIGHT, y - 2 * mm)
    return y - 8 * mm


def footer(c, page_no, total):
    c.setFont("Helvetica", 7)
    c.drawString(LEFT, 14 * mm, "Generated electronically. No signature required.")
    c.drawCentredString(A4[0] / 2, 9 * mm, "Page %d of %d" % (page_no, total))
    c.drawRightString(RIGHT, 14 * mm, "Sterling Union Bank AG")


def row(c, y, date, desc, wd, dep, bal):
    c.setFont("Helvetica", 8)
    c.drawString(COL_DATE, y, date)
    c.drawString(COL_DESC, y, desc[0])
    c.drawRightString(COL_WD, y, money(wd) if wd else "")
    c.drawRightString(COL_DEP, y, money(dep) if dep else "")
    c.drawRightString(COL_BAL, y, money(bal))
    y -= 5 * mm
    for extra in desc[1:]:
        c.setFont("Helvetica", 8)
        c.drawString(COL_DESC, y, extra)
        y -= 5 * mm
    return y


def build():
    c = canvas.Canvas(OUT, pagesize=A4)
    total = 2
    y = header(c)

    c.setFont("Helvetica", 8)
    for line in [ACCOUNT, "Speicherstrasse 8", "60327 Frankfurt am Main", ""]:
        c.drawString(COL_DATE, y, line)
        y -= 4.5 * mm

    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DESC, y, "BALANCE B/F")
    c.drawRightString(COL_BAL, y, money(OPENING))
    y -= 7 * mm

    bal = OPENING
    ledger = []
    for i, (date, desc, wd, dep) in enumerate(TXNS):
        bal = bal - (wd or 0) + (dep or 0)
        ledger.append((date, desc, wd, dep, bal))
        y = row(c, y, date, desc, wd, dep, bal)
        if i == PAGE_BREAK_AFTER:
            footer(c, 1, total)
            c.showPage()
            y = header(c)

    y -= 3 * mm
    c.line(LEFT, y + 2 * mm, RIGHT, y + 2 * mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DESC, y - 3 * mm, "BALANCE C/F")
    c.drawRightString(COL_BAL, y - 3 * mm, money(bal))
    footer(c, 2, total)
    c.save()
    return ledger, bal


if __name__ == "__main__":
    ledger, closing = build()
    mv = sum((dep or 0) - (wd or 0) for _, _, wd, dep, _ in ledger)
    print("wrote %s" % OUT)
    print("rows        : %d" % len(ledger))
    print("opening     : %s" % money(OPENING))
    print("movements   : %s" % money(mv))
    print("closing     : %s" % money(closing))
    print("reconciles  : %s" % (abs(OPENING + mv - closing) < 0.01))
