# Statement & Invoice PDF → Reconciled Rows (n8n workflow)

**Every row is checked against the statement's own balance column. Each one comes
back reconciled, flagged, or — when there's nothing to check it against — marked
unverified. Nothing wrong ever passes as right.**

Most PDF-extraction workflows pipe the file straight into a vision model and
hope. That's why the numbers drift, and why you don't find out until a client
does. This one is built the other way round: deterministic parsing produces
every figure, the LLM only decides which column each figure belongs to, and then
arithmetic proves the result.

**Tested on a real 86-transaction card statement: 100% of rows extracted** —
every date resolved, every amount parsed, wrapped descriptions rejoined, repeated
page headers stripped. Not a hand-picked sample; the actual output on a live
statement whose layout the workflow had never seen.

---

## What it actually handles

Real statements break naive parsers in the same few ways. This workflow is built
for them specifically:

- **Descriptions that wrap onto a second line** — stitched back into one row, not
  split into two.
- **Transactions split across a page break** — amounts on page 1, description
  continuing on page 2. Rejoined correctly.
- **Accounting-parentheses negatives** — `(1,250.00)` read as −1,250.00, not
  1,250.00. Also handles trailing CR/DR markers.
- **Repeated page headers and footers** — removed by cross-page frequency, so
  they never leak into a description field.
- **DD/MM vs MM/DD ambiguity** — the statement's date order is inferred once from
  the whole document, then applied. No more `02/06` silently becoming 6 February
  when it meant 2 June.
- **Scanned PDFs** — automatically routed to OCR when the text layer is missing.

## The part nobody else ships

A reconciliation pass that runs after extraction:

- Running balance walk — `balance[n-1] ± movement = balance[n]` on every row
- Opening + sum of movements = closing
- A second, independent check against the statement's **printed** closing figure,
  which catches an entire row going missing — the one error a balance walk cannot
  see on its own
- Confidence scored **per field**, not per row, so an ambiguous amount flags the
  amount and not the clean date beside it
- Three honest outcomes per row — **reconciled** (checked and it adds up),
  **flagged** (checked and it doesn't), **unverified** (no balance to check it
  against, e.g. the opening row or a card statement). A row is never counted as
  reconciled unless it was actually verified.

Reconciled rows go to CSV or Google Sheets. Flagged rows go to a review queue with
the page and row number attached. You always know which rows you can trust — and
which ones the workflow couldn't vouch for.

## What's included

- The n8n workflow (`.json`, import and run)
- A variant pre-wired for Google Gemini as well as OpenAI
- A headless test variant that runs with **no credentials at all**, so you can
  verify the pipeline before wiring up a model
- A synthetic demo statement PDF with all the hard cases baked in, plus the
  script that generates it — so you can produce your own test fixtures
- A standalone test harness for iterating on the parsing logic outside n8n

## Requirements

- n8n (tested on 2.35.7, self-hosted or cloud)
- An LLM credential — OpenAI or Google Gemini
- Optional: an OCR provider, only if you're processing scanned PDFs

## What it does not do

Straight, because you'll find out anyway:

- It is **not** a universal parser for every bank on earth. It is built around
  statements with a running balance column, which is what makes the
  reconciliation check possible. Layouts without one will extract but won't
  reconcile.
- The OCR branch is wired but you supply the provider and credentials.
- Column-collision PDFs — where two columns physically overlap in the text layer
  — are a fault in the source document, and no parser recovers those cleanly.

---

*Built by someone who has spent a lot of time on why bank PDFs extract badly. The
parsing logic is the product; the n8n wiring around it is the easy part.*
