# Statement & Invoice PDF → Reconciled Rows

Thank you for buying this. It's an n8n workflow that turns a statement or invoice
PDF into structured rows, and **checks every row against the statement's own
balance column** — anything that doesn't add up is flagged instead of shipped.

---

## What's in this download

| File | What it is |
|---|---|
| `workflow.json` | The main workflow. Uses OpenAI for the one LLM step. |
| `workflow.gemini.json` | Same workflow, wired for Google Gemini instead. |
| `workflow.test.json` | A headless version that runs with **no API key at all** — use it to see the pipeline work before you wire up a model. |
| `demo_statement.pdf` | A synthetic statement with the hard cases baked in (wrapped rows, a page-split transaction, a `(1,250.00)` negative). Safe to test with. |
| `sample_reconciled_rows.csv` | Real output from running the workflow on the demo — the 15 clean rows, so you can see the exact shape you get back. |
| `sample_flagged_for_review.csv` | The one row the workflow flagged in that run (the model mislabelled a debit as a credit), with the balance-mismatch reason — this is what a caught error looks like. |

## Requirements

- n8n (self-hosted or cloud) — built and tested on 2.35.x
- One LLM credential: **OpenAI** or **Google Gemini**
- Optional: an OCR provider (e.g. Mistral OCR), only if you process *scanned* PDFs

---

## Quick start (5 minutes)

**1. Import the workflow.**
In n8n: *Workflows → Import from File → `workflow.json`* (or the Gemini one).

**2. Add your LLM credential.**
Open the **Chat Model** node, click its credential dropdown → **Create new**,
paste your OpenAI or Gemini API key, save.

**3. Run it.**
Open the **Upload PDF** form (the trigger node gives you a URL), upload
`demo_statement.pdf`, and submit. You'll get back reconciled rows as CSV, with a
separate list of anything flagged.

**Want to see it work first, with no key?** Import `workflow.test.json` instead —
it reads a PDF from disk and uses a built-in stub in place of the LLM, so the
whole pipeline runs with nothing to configure. On the demo statement it
reconciles all 16 rows.

---

## How it works (so you can adapt it)

Two nodes do the real work; the rest is standard n8n plumbing you can rewire
freely.

- **Layout normalisation** (a Code node) turns raw PDF text into clean rows:
  strips repeated page headers/footers, rejoins descriptions that wrap onto a
  second line, stitches transactions split across a page break, parses
  accounting-parentheses negatives, and works out the statement's date order
  (DD/MM vs MM/DD) from the document itself.

- **Validate & reconcile** (a Code node) proves the result: it walks the running
  balance (`balance[n-1] ± movement = balance[n]`), checks opening + movements =
  closing, compares against the statement's *printed* closing figure, and scores
  confidence per field. Rows that fail land in the review output with their page
  and row number.

To point this at your own statement format, those two nodes are where you'll
make changes — the comments inside them explain each step.

---

## Honest limits

- Built around statements that have a **running balance column** — that's what
  makes the reconciliation check possible. Layouts without one (many credit-card
  statements) will extract fine but won't reconcile.
- The OCR branch is wired but you supply the provider and its credentials.
- If two columns physically overlap in a PDF's text layer, that's a fault in the
  source document and no parser recovers it cleanly.

---

## Support

Found a statement layout it stumbles on? Send me the (redacted) PDF and I'll take
a look — the parsing logic is the part I keep improving.
