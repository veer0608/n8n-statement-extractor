"""
Generate a synthetic bank statement PDF for the n8n statement extractor demo.

FICTIONAL. No real account, person, or institution. Safe to ship publicly as a
sample file - which is the point: never put a real statement in a product.

Three failure cases are deliberately baked in, because they are what break the
cheap "PDF -> LLM -> JSON" templates:

  1. A description that WRAPS onto a second line.
  2. A transaction SPLIT ACROSS A PAGE BREAK (row starts on page 1, its
     description continues on page 2).
  3. A negative rendered in ACCOUNTING PARENTHESES - (1,250.00).

Plus the ordinary furniture that trips row detection: a repeated page header,
a repeated footer, page numbers, and an address block before the first row.

The ledger is arithmetically exact: opening + sum(movements) == closing.
So a correct parser reconciles 100% of rows. Any flag is the parser's fault.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = "demo_statement.pdf"

BANK = "Meridian Commercial Bank"
ACCOUNT = "Northwind Trading Co."
ACC_NO = "XXXXXX4417"
PERIOD = "01 Jun 2026 to 30 Jun 2026"
OPENING = 784_320.00

# (date, description_lines, debit, credit)
# description_lines is a list: >1 entry means the description wraps.
TXNS = [
    ("02/06/2026", ["NEFT IN  ORION LOGISTICS PVT LTD"], None, 42_500.00),
    ("03/06/2026", ["UPI/P2M/419283746/SWIFTPARCEL"], 1_845.50, None),
    ("05/06/2026", ["RTGS OUT  QUARTERLY VENDOR SETTLEMENT -",
                    "HARBOURSIDE SUPPLIES LLP  INV 2026/Q1/0884"], 96_400.00, None),  # CASE 1: wrap
    ("07/06/2026", ["CHQ DEP 004512"], None, 18_000.00),
    ("09/06/2026", ["BANK CHARGES - ACCOUNT MAINTENANCE"], 590.00, None),
    ("11/06/2026", ["IMPS IN  D. RAGHAVAN"], None, 7_250.00),
    # CASE 3: a REVERSAL posted as a negative debit, printed (1,250.00).
    ("12/06/2026", ["CARD PAYMENT REVERSAL - MERCHANT DISPUTE"], -1_250.00, None),
    ("14/06/2026", ["SALARY DISBURSEMENT JUN 2026 BATCH 1"], 212_800.00, None),
    # CASE 2: this row is forced to straddle the page break
    ("16/06/2026", ["NEFT OUT  ANNUAL SOFTWARE LICENCE RENEWAL",
                    "CLEARVIEW ANALYTICS - CONTRACT CV-8871-R"], 58_900.00, None),
    ("18/06/2026", ["INTEREST CREDITED"], None, 1_402.75),
    ("20/06/2026", ["UPI/P2M/551209384/FUELMART"], 4_310.00, None),
    ("22/06/2026", ["NEFT IN  KESTREL INDUSTRIES"], None, 155_000.00),
    ("25/06/2026", ["GST PAYMENT - JUN 2026"], 38_745.25, None),
    ("27/06/2026", ["ATM WDL  MG ROAD BR"], 15_000.00, None),
    ("29/06/2026", ["NEFT OUT  RENT - PREMISES 4TH FLR"], 72_000.00, None),
    ("30/06/2026", ["IMPS IN  SETTLEMENT ADJUSTMENT"], None, 9_180.00),
]

# Row index forced to be the last on page 1, so its wrapped description spills
# onto page 2. Index 8 is the ANNUAL SOFTWARE LICENCE row.
SPLIT_AT = 8

LEFT = 18 * mm
RIGHT = A4[0] - 18 * mm
COL_DATE = LEFT
COL_DESC = LEFT + 24 * mm
# Right edges. Kept far enough apart that no two columns can collide at 8pt -
# overlapping columns produce a mangled text layer (42,5008.2060,820.00) and
# that is a fault in the generator, not something a parser should have to fix.
COL_DEBIT = LEFT + 112 * mm
COL_CREDIT = LEFT + 142 * mm
COL_BAL = RIGHT


def money(v):
    """Accounting format. Negative -> parentheses. CASE 3 lives here."""
    if v < 0:
        return "({:,.2f})".format(abs(v))
    return "{:,.2f}".format(v)


def header(c, page_no):
    """Repeated on EVERY page - the furniture a parser must learn to drop."""
    c.setFont("Helvetica-Bold", 13)
    c.drawString(LEFT, A4[1] - 20 * mm, BANK)
    c.setFont("Helvetica", 8)
    c.drawString(LEFT, A4[1] - 25 * mm, "Statement of Account")
    c.drawRightString(RIGHT, A4[1] - 20 * mm, "Account: %s" % ACC_NO)
    c.drawRightString(RIGHT, A4[1] - 25 * mm, "Period: %s" % PERIOD)
    c.line(LEFT, A4[1] - 28 * mm, RIGHT, A4[1] - 28 * mm)

    y = A4[1] - 34 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DATE, y, "Date")
    c.drawString(COL_DESC, y, "Description")
    c.drawRightString(COL_DEBIT, y, "Debit")
    c.drawRightString(COL_CREDIT, y, "Credit")
    c.drawRightString(COL_BAL, y, "Balance")
    c.line(LEFT, y - 2 * mm, RIGHT, y - 2 * mm)
    return y - 8 * mm


def footer(c, page_no, total):
    """Repeated footer + page number - more furniture."""
    c.setFont("Helvetica", 7)
    c.drawString(LEFT, 14 * mm,
                 "This is a computer generated statement and does not require a signature.")
    c.drawCentredString(A4[0] / 2, 9 * mm, "Page %d of %d" % (page_no, total))
    c.drawRightString(RIGHT, 14 * mm, BANK)


def draw_row(c, y, date, desc_lines, debit, credit, balance, first_line_only=False):
    c.setFont("Helvetica", 8)
    c.drawString(COL_DATE, y, date)
    c.drawString(COL_DESC, y, desc_lines[0])
    if not first_line_only:
        c.drawRightString(COL_DEBIT, y, money(debit) if debit else "")
        c.drawRightString(COL_CREDIT, y, money(credit) if credit else "")
        c.drawRightString(COL_BAL, y, money(balance))
    return y - 5 * mm


def build():
    c = canvas.Canvas(OUT, pagesize=A4)
    total_pages = 2

    # --- page 1 -------------------------------------------------------------
    y = header(c, 1)

    # Address preamble - lines before the first transaction, must be discarded.
    c.setFont("Helvetica", 8)
    for line in [ACCOUNT, "Unit 12, Harbour Business Park", "Bengaluru 560103", ""]:
        c.drawString(COL_DATE, y, line)
        y -= 4.5 * mm

    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DESC, y, "OPENING BALANCE")
    c.drawRightString(COL_BAL, y, money(OPENING))
    y -= 7 * mm

    balance = OPENING
    ledger = []

    for i, (date, desc, debit, credit) in enumerate(TXNS):
        balance = balance - (debit or 0) + (credit or 0)
        ledger.append((date, desc, debit, credit, balance))

        if i == SPLIT_AT:
            # CASE 2: first line + amounts on page 1, continuation on page 2.
            y = draw_row(c, y, date, desc, debit, credit, balance)
            footer(c, 1, total_pages)
            c.showPage()
            y = header(c, 2)
            c.setFont("Helvetica", 8)
            c.drawString(COL_DESC, y, desc[1])   # continuation, stranded on p2
            y -= 5 * mm
            continue

        y = draw_row(c, y, date, desc, debit, credit, balance)
        # CASE 1: wrapped description, same page.
        if len(desc) > 1:
            c.setFont("Helvetica", 8)
            c.drawString(COL_DESC, y, desc[1])
            y -= 5 * mm

    y -= 3 * mm
    c.line(LEFT, y + 2 * mm, RIGHT, y + 2 * mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DESC, y - 3 * mm, "CLOSING BALANCE")
    c.drawRightString(COL_BAL, y - 3 * mm, money(balance))

    footer(c, 2, total_pages)
    c.save()
    return ledger, balance


if __name__ == "__main__":
    ledger, closing = build()
    movements = sum((cr or 0) - (db or 0) for _, _, db, cr, _ in ledger)
    print("wrote %s" % OUT)
    print("rows            : %d" % len(ledger))
    print("opening         : %.2f" % OPENING)
    print("sum(movements)  : %.2f" % movements)
    print("closing         : %.2f" % closing)
    print("reconciles      : %s" % (abs(OPENING + movements - closing) < 0.01))
    print("wrapped rows    : %d" % sum(1 for _, d, _, _, _ in ledger if len(d) > 1))
