# Statement & Invoice PDF → Reconciled Rows (n8n workflow)

I kept running into the same thing: you point an n8n workflow at a bank
statement, it pipes the PDF into a vision model, and the JSON that comes back
looks fine. Then a client spots a number that's off by a digit, and you're the
one who shipped it.

So I built this one backwards. The parsing is deterministic — it pulls every
figure out of the text itself. The AI only decides which column a figure belongs
to (debit, credit, balance). Then plain arithmetic checks the result against the
statement's own running balance. If a row doesn't add up, it gets flagged instead
of handed to you as fact.

I ran it against a real 86-transaction card statement — a layout it had never
seen — and it pulled every row: dates resolved, amounts parsed, wrapped
descriptions rejoined, page headers stripped. 100%.

---

## The stuff that usually breaks extraction

Real statements go wrong in a handful of predictable ways, and this is built for
each of them:

- Descriptions that wrap onto a second line — stitched back into one row.
- Transactions split across a page break, with the amounts on page 1 and the
  description trailing onto page 2. Rejoined.
- Accounting-style negatives like `(1,250.00)` — read as −1,250.00, not positive.
  Trailing CR/DR markers too.
- Repeated page headers and footers, dropped by how often they recur, so they
  never end up inside a description.
- The DD/MM vs MM/DD mess — it works the date order out once from the whole
  document and applies it, so `02/06` doesn't quietly become 6 February when it
  meant the 2nd of June.
- Scanned PDFs get routed to OCR automatically when there's no text layer.

## The reconciliation is the actual product

This is the bit the cheap templates skip. After extraction, it:

- Walks the running balance row by row — previous balance ± this movement should
  equal the new balance.
- Checks opening + all movements against the closing figure.
- Cross-checks that against the *printed* closing balance too, which is the only
  way to notice a row that went missing entirely (drop a row and everything left
  still chains up fine — the printed total is what gives it away).
- Scores confidence per field, not per row, so a dodgy amount gets flagged
  without dragging down the clean date sitting next to it.

Every row ends up in one of three states: reconciled (checked, it adds up),
flagged (checked, it doesn't), or unverified (nothing to check it against — the
opening row, or a statement with no balance column). Nothing gets called
reconciled unless it actually was. Clean rows go out to CSV or Sheets; flagged
ones land in a review queue with their page and row number.

## It caught a real mistake while I was testing it

I ran it against a live model and the AI got one row wrong — labelled a salary
payment as money coming *in* when the balance clearly showed it going *out*.

The workflow caught it: `balance mismatch: expected 967,284.50, got 541,684.50`,
straight to review. The other fifteen rows were fine.

What I like about that example: the closing balance still matched. The error was
sitting in the middle, which is exactly where a "does the total add up" check
looks right and misses it. The row-by-row walk is the thing that noticed. Models
will slip on ambiguous rows now and then — the point isn't that it never happens,
it's that you find out before it reaches the books.

## What you get

- The workflow itself — import the JSON and go.
- A second copy pre-wired for Gemini if you'd rather use that than OpenAI.
- A no-credentials test version, so you can watch the whole thing run before you
  plug in any API key.
- A synthetic demo statement with all the awkward cases baked in, plus the script
  that makes it — handy for building your own test files.
- A small harness for poking at the parsing logic outside n8n.

## What you'll need

- n8n (I built and tested on 2.35.7, self-hosted or cloud).
- An OpenAI or Gemini key.
- An OCR provider, but only if you're feeding it scanned PDFs.

## What it won't do

Rather you know up front:

- It's not a magic parser for every bank on earth. It's built around statements
  that have a running balance column — that column is what makes the
  reconciliation possible. Statements without one (most credit cards) will still
  extract, they just won't reconcile.
- The OCR branch is wired up, but the provider and key are yours to supply.
- If two columns physically overlap in the PDF's text layer, that's a broken
  source document and no parser gets those back cleanly.

---

*I've spent more hours than I'd like to admit on why bank PDFs come out wrong.
The parsing and the reconciliation are the real work here; the n8n wiring around
them is the easy part.*
