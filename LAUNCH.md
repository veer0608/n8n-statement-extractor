# Launch announcement drafts

Three platform variants of the same launch. Verified claims only — "86/86
extracted" (real card statement) and "16/16 reconciled" (synthetic demo).
Nothing claims reconciliation proven on a real balance-column statement, because
it isn't yet.

Launch discount: code `LAUNCH25`, $10 off (→ $19), first 25 uses. Auto-apply
link: `https://veer0608.gumroad.com/l/statement-extractor?offer_code=LAUNCH25`

---

## X / Twitter

Lead post:

> Most n8n PDF-extraction templates pipe the statement into a vision model and
> hope. That's why the numbers drift — and you find out when a client does.
>
> I built one that works backwards: parse deterministically, let the LLM only
> assign columns, then **check every row against the statement's own balance**.
> Anything that doesn't add up gets flagged, not shipped.
>
> Real 86-transaction statement: 86/86 rows extracted, correct dates, wrapped
> lines rejoined.
>
> Launch: first 25 copies at $19 (then $29) 👇
> veer0608.gumroad.com/l/statement-extractor?offer_code=LAUNCH25

Optional thread reply:

> The two nodes that matter: one rebuilds real rows from messy PDF text
> (stripping repeated headers, stitching page-split transactions, reading
> (1,250.00) negatives). The other proves the result arithmetically. Everything
> else is standard n8n you can rewire.

---

## LinkedIn

> I kept hitting the same wall: every n8n workflow for extracting bank statements
> would quietly get a number wrong, and there was no way to know which rows to
> trust.
>
> So I built one around a different rule — the LLM never touches a number it
> could invent. Deterministic parsing produces every figure; the model only
> decides which column it belongs to; then arithmetic checks every row against
> the statement's own running balance. If a row doesn't reconcile, it's flagged
> for review instead of silently shipped.
>
> Tested on a real 86-transaction statement: 100% of rows extracted, across a
> layout it had never seen.
>
> It's live on Gumroad — first 25 copies at $19. Link in comments.
> (Honest note: the reconciliation check needs a statement with a balance column,
> so credit-card statements extract but don't reconcile. I say so on the listing.)

---

## r/n8n

Before posting, check the sub's current self-promotion rules — some weeks require
a flair or restrict promo to a specific thread.

**Title:** Built an n8n statement-PDF extractor that reconciles every row against
the balance column (or flags it)

**Body:**

> Got tired of PDF→LLM workflows drifting on real statements, so I built one that
> parses deterministically and only uses the LLM to assign debit/credit/balance —
> then walks the running balance to prove each row. Flagged rows go to a review
> queue with page + row number.
>
> Handles the stuff that breaks naive parsers: wrapped descriptions, transactions
> split across a page break, (1,250.00) negatives, DD/MM vs MM/DD ambiguity,
> scanned PDFs via OCR. Comes with a no-API-key test variant so you can see it run
> before wiring up a model.
>
> Launch price for this sub: $19 (code LAUNCH25). Happy to answer anything about
> how the reconciliation node works.

---

## X / Twitter — technical thread (the two nodes)

A build-in-public deep dive. Higher-credibility play for the dev audience; the
bugs in 4, 7 and 8 are the engagement drivers.

**1/**
> An n8n workflow to turn bank-statement PDFs into clean rows is ~10 nodes. Nine
> are stock plumbing. Two do all the real work — and they're where every cheap
> template cuts the corner that makes it wrong.
>
> Here's what's actually in them 🧵

**2/**
> Node 1: layout normalisation.
>
> Raw PDF text isn't rows. One transaction can span three lines. A page header
> repeats every page. A row can split across a page break.
>
> Feed that straight to an LLM and it hallucinates. So I rebuild real rows
> *deterministically* first.

**3/**
> The rule for stitching: a new transaction starts with a date. Everything until
> the next date is a continuation of the current row.
>
> That one rule rejoins wrapped descriptions AND page-split transactions — the
> description stranded on page 2 gets pulled back onto its row.

**4/**
> Then the bug that would've shipped silently:
>
> `new Date("14/06/2026")` → Invalid Date (JS assumes MM/DD).
> Worse: `new Date("02/06/2026")` → 6 February, not 2 June.
>
> Days ≤ 12 corrupt with no error. Days > 12 throw. Half your rows wrong, zero
> warnings.

**5/**
> Fix: infer the statement's date order *once* from the whole document — find any
> component > 12, that settles DD/MM vs MM/DD — then parse explicitly.
>
> When every day is ≤ 12 it's genuinely undecidable, so it flags low confidence
> instead of guessing.

**6/**
> Node 2: reconciliation. The part nobody else ships.
>
> It walks the running balance: `balance[n-1] ± movement = balance[n]`, on every
> row. A row that doesn't add up gets flagged — with its page and row number —
> instead of silently shipped.

**7/**
> One check I'm proud of: it also compares against the statement's *printed*
> closing figure.
>
> A running-balance walk can't see a row that went missing entirely — every
> surviving row still chains correctly. Only the printed-total comparison catches
> the gap.

**8/**
> Last one, a lesson: my terminator rule `closing\s+bal\b` never matched
> "CLOSING BALANCE".
>
> A word boundary can't sit between "bal" and "ance". It failed *identically* to
> having no rule at all — no error, just wrong. `\b` → `\w*`.
>
> Silent bugs are the expensive ones.

**9/**
> All of this runs in n8n. Full workflow + a no-API-key test variant + a demo PDF
> with the hard cases baked in:
>
> veer0608.gumroad.com/l/statement-extractor?offer_code=LAUNCH25
> (first 25 at $19)
