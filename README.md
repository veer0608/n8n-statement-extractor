# Statement & Invoice PDF → Reconciled Rows

[![Get it on Gumroad](https://img.shields.io/badge/Gumroad-Get%20the%20template-ff90e8?style=for-the-badge&logo=gumroad&logoColor=white)](https://veer0608.gumroad.com/l/statement-extractor)

An n8n workflow that turns a bank statement or invoice PDF into structured rows,
where **every row is arithmetically reconciled against the statement's own
balance column, or flagged**.

Built as a sellable n8n template. The market rationale is in
`../n8n_paid_ai_agents.xlsx`: document/PDF extraction is the thinnest-supplied
theme on n8n's library (17 paid listings against 177 free ones averaging 3,034
views — a demand-to-supply ratio of 178, four times any other category), and
eleven of those seventeen are resume screeners. Nobody is selling accurate
structured extraction.

## The design rule

**The LLM never touches a number it could invent.**

Deterministic extraction produces the values, the LLM only assigns structure,
then arithmetic proves the result. Competing templates pipe the PDF straight
into a vision model and hope. That is why they drift.

```
[1] Form Trigger (PDF upload)
[2] Extract from File          text layer + per-page char count
[3] Code: triage               <80 chars/page ⇒ scanned, else digital
[4] Switch ──── scanned ──► HTTP: OCR ──┐
     └───────── digital ────────────────┤
[5] Code: layout normalisation  ◄── THE MOAT
      strip repeated headers/footers by cross-page frequency
      drop page numbers and address preamble
      stitch wrapped descriptions and page-split rows
      parse (1,234.56) and CR/DR negatives
      infer the statement's date order once, emit ISO
      capture printed opening and closing balances
[6] LLM Chain + Structured Output Parser   (temp 0, batched per page)
      schema-enforced; receives resolved values, assigns roles only
[7] Code: validation & reconciliation  ◄── THE PROOF
      running balance: balance[n-1] ± movement == balance[n]
      opening + Σmovements == closing
      independent check against the PRINTED closing figure
      per-field confidence, not per-row
[8] IF reconciled ─┬─ pass ─► CSV / Sheets
                   └─ fail ─► review queue (page + row number)
[9] Respond: download link + {rows, flagged, confidence}
```

Nodes 5 and 7 are the product. Everything else is stock n8n.

## Files

| File | Purpose |
|---|---|
| `workflow.json` | The shipping copy. OpenAI-backed — what most buyers already have wired. |
| `workflow.test.json` | Headless variant: file read instead of form upload, deterministic stub instead of the LLM. Needs **no credentials**. |
| `workflow.gemini.json` | Headless variant with the real LLM chain on Gemini. Needs a Google Gemini credential (see below). |
| `make_test_variant.py` / `make_gemini_variant.py` | Regenerate the variants from `workflow.json`. Edit the source, never the variants. |
| `make_demo_pdf.py` | Generates `demo_statement.pdf`. Ledger arithmetic exact by construction. |
| `test_demo_parses.py` | Python port of nodes 5 and 7, run against the demo PDF. |

## The demo PDF

Fully fictional — safe to ship publicly. Never put a real statement in a
product. Three deliberate killers are baked in, because they are what break the
cheap templates:

1. A description that **wraps** onto a second line.
2. A transaction **split across a page break** — amounts on page 1, description
   continuing on page 2.
3. A negative in **accounting parentheses**, `(1,250.00)`.

Plus repeated page headers, footers, page numbers, and an address preamble.

## Verified state

`workflow.test.json` executed in real n8n (v2.35.7):

```
rows = 16   flagged = 0   reconciledPct = 100
statementReconciles = True   printedClosingMatches = True
dateOrder = DMY   dateOrderConfident = True
printedOpening = 784,320   printedClosing = 518,312
```

Every node except the LLM is proven in the real runtime.

**Not yet verified:** the LLM node filling the JSON schema against a live model,
and the OCR branch, which is stubbed against Mistral and needs credentials plus
a real document URL.

## LLM provider

`workflow.json` ships on OpenAI because that is what most people already have
wired up. `workflow.gemini.json` is the same pipeline on Google Gemini, which is
a better choice for long runs on a free tier — Groq's free tier enforces a
tokens-per-day ceiling that appears in no response header, so a batch can die
partway with nothing to show.

Either way, create the credential in the n8n UI first:
**Credentials → Add credential → *your provider* → paste key → Save.** There is
no CLI route around this, because the credential holds a secret.

A note on running a local model instead: it removes the credential step, but
verify the runtime actually works before relying on it. Ollama on the machine
this was built on returned corrupted output for every model and never set the
`done` flag — two unrelated models failed identically, so it was the runtime,
not the weights.

One Node-on-Windows trap if any local HTTP service is wired in: Node 24's
`fetch` resolves `localhost` to IPv6 `::1` first, so a service bound to IPv4
only needs an explicit `127.0.0.1` in its base URL. curl hides this by falling
back to IPv4.

## Two bugs worth not reintroducing

**Dates.** `new Date("14/06/2026")` is Invalid Date, because JS assumes
MM/DD/YYYY. Worse, `new Date("02/06/2026")` succeeds and returns 6 February
instead of 2 June — days ≤ 12 corrupt *silently*, days > 12 throw. Node 5 now
infers the statement's date order once from the whole document (looking for any
component > 12) and emits ISO. When every day is ≤ 12 the document is genuinely
undecidable, so it assumes DMY and exposes `dateOrderConfident: false` rather
than pretending. The LLM is handed a resolved date and told to copy it verbatim.

**The terminator regex.** `closing\s+bal\b` never matches `CLOSING BALANCE` —
a word boundary cannot sit between `bal` and `ance`. It failed silently and
identically to having no rule at all. It is `bal\w*` for that reason.

## Running the headless test

```bash
cd "C:/Users/veera/claude/n8n-statement-extractor" && python test_demo_parses.py
```

For the n8n run, `N8N_RESTRICT_FILE_ACCESS_TO` must point at this directory —
n8n blocks filesystem reads by default.

Note the Python port is a *weaker* check than the n8n run: it does not validate
dates, which is why it passed a workflow that was corrupting them.
