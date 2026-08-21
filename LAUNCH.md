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

> Most n8n statement-extraction templates just throw the PDF at a vision model
> and hope. The numbers drift, and you usually find out when a client does.
>
> Built one that works the other way round — parse deterministically, let the AI
> only pick which column each number is, then check every row against the
> statement's own balance. If it doesn't add up, it gets flagged, not shipped.
>
> Ran it on a real 86-transaction statement: every row extracted, dates right,
> wrapped lines put back together.
>
> First 25 copies at $19 (then $29) 👇
> veer0608.gumroad.com/l/statement-extractor?offer_code=LAUNCH25

Optional thread reply:

> Two nodes do the real work. One rebuilds actual rows out of messy PDF text —
> repeated headers, page-split transactions, `(1,250.00)` negatives. The other
> proves the result with arithmetic. The rest is stock n8n you can rewire however
> you like.

---

## LinkedIn

> Same wall, over and over: an n8n workflow pulls a bank statement into JSON, it
> looks right, and one number is quietly wrong — with no way to tell which.
>
> So I built this one around a rule I trust: the model never touches a number it
> could make up. The parsing produces every figure; the AI just decides which
> column it goes in; then the arithmetic checks each row against the statement's
> running balance. Anything that doesn't reconcile gets flagged for review rather
> than shipped.
>
> I tested it on a real 86-transaction statement — a layout it had never seen —
> and it pulled every row.
>
> It's on Gumroad now, first 25 copies at $19. Link in the comments.
>
> One honest caveat: the reconciliation needs a statement with a balance column,
> so credit-card statements extract fine but don't reconcile. That's on the
> listing too — I'd rather you know before you buy.

---

## r/n8n

Before posting, check the sub's current self-promotion rules — some weeks they
want a flair, or keep promo to one thread.

**Title:** I built an n8n statement-PDF extractor that reconciles every row
against the balance column (or flags it)

**Body:**

> Got fed up with PDF→LLM workflows drifting on real statements, so I built one
> that parses deterministically and only lets the model assign
> debit/credit/balance — then walks the running balance to check each row. Rows
> that don't add up go to a review queue with the page and row number.
>
> It handles the usual troublemakers: wrapped descriptions, transactions split
> across a page break, `(1,250.00)` negatives, the DD/MM vs MM/DD mess, scanned
> PDFs through OCR. There's a no-API-key test version so you can watch it run
> before wiring up a model.
>
> Launch price for this sub is $19 (code LAUNCH25). Happy to get into how the
> reconciliation node works if anyone's curious — it's the part I'm proud of.

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
