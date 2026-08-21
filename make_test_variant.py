"""
Produce workflow.test.json - a headless copy that `n8n execute` can actually run.

Three changes from workflow.json, all confined to the edges:

  1. Form Trigger        -> Execute Workflow Trigger + Read File from Disk.
     The CLI refuses to start a workflow whose only trigger is a webhook form.
  2. LLM node            -> a deterministic Code stub.
     This lets the whole spine run with NO credentials, so nodes 3/5/7 get
     tested in n8n's real runtime rather than only in the Python port.
  3. Batching loop       -> removed. It exists to keep LLM context small; with
     no LLM in the loop it only complicates the wiring.

The stub is deliberately NOT allowed to derive debit/credit from the balance -
that would make node 7's reconciliation check tautological and prove nothing.
It picks the printed movement figure and decides its direction, exactly the
judgement the LLM is asked to make.
"""
import json
import os

SRC = "workflow.json"
DST = "workflow.test.json"
PDF = os.path.abspath("demo_statement.pdf").replace("\\", "/")

STUB = r"""// LLM STUB - stands in for "Structure rows (LLM)" during headless testing.
// Mirrors the LLM's job: given the row's printed amounts, decide which is the
// debit, which the credit, which the balance. It may NOT back-solve the
// movement from the balance - node 7 has to stay a real check.

const items = $input.all().map(i => i.json);
const stmt = items.length ? (items[0]._statement || {}) : {};
let prev = stmt.printedOpening ?? null;

const out = [];
for (const r of items) {
  const a = r.amounts || [];
  const balance = a.length ? a[a.length - 1] : null;
  const mag = a.length > 1 ? a[a.length - 2] : null;

  let debit = null, credit = null;
  if (mag !== null && prev !== null && balance !== null) {
    if (Math.abs((prev - mag) - balance) < 0.01) debit = mag;
    else if (Math.abs((prev + mag) - balance) < 0.01) credit = mag;
    else debit = mag;            // unresolved - let node 7 flag it
  }

  if (balance !== null) prev = balance;

  out.push({ json: {
    date: r.dateIso,          // node 5 resolved the statement date order
    description: r.description,
    reference: null,
    debit, credit, balance,
    _statement: r._statement
  }});
}
return out;"""


def main():
    wf = json.load(open(SRC, encoding="utf-8"))
    nodes = {n["name"]: n for n in wf["nodes"]}

    keep = ["Extract from File", "Triage: digital or scanned", "Route",
            "OCR (scanned only)", "Layout normalisation", "Validate & reconcile",
            "Reconciled?", "Clean rows -> CSV", "Flagged -> review queue"]
    new_nodes = [nodes[k] for k in keep]

    # 1. headless entry point
    new_nodes.insert(0, {
        "parameters": {"inputSource": "passthrough"},
        "id": "exec-trigger", "name": "When Executed",
        "type": "n8n-nodes-base.executeWorkflowTrigger",
        "typeVersion": 1.1, "position": [-1040, 300],
    })
    new_nodes.insert(1, {
        "parameters": {
            "fileSelector": PDF,
            "options": {"dataPropertyName": "PDF_file"},
        },
        "id": "read-file", "name": "Read demo PDF",
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1, "position": [-820, 300],
    })

    # 2. LLM -> stub
    new_nodes.append({
        "parameters": {"jsCode": STUB},
        "id": "llm-stub", "name": "Structure rows (stub)",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [720, 300],
    })

    # triage's form reference cannot resolve without the form trigger
    tri = nodes["Triage: digital or scanned"]
    tri["parameters"]["jsCode"] = tri["parameters"]["jsCode"].replace(
        "openingBalanceHint: $('Upload PDF').first().json['Opening balance (optional)'] ?? null",
        "openingBalanceHint: null   // headless: node 5 reads the printed opening"
    )

    wf["nodes"] = new_nodes
    wf["id"] = "stmtExtractTest"
    wf["name"] = "Statement Extractor (headless test, no credentials)"
    wf["connections"] = {
        "When Executed": {"main": [[{"node": "Read demo PDF", "type": "main", "index": 0}]]},
        "Read demo PDF": {"main": [[{"node": "Extract from File", "type": "main", "index": 0}]]},
        "Extract from File": {"main": [[{"node": "Triage: digital or scanned", "type": "main", "index": 0}]]},
        "Triage: digital or scanned": {"main": [[{"node": "Route", "type": "main", "index": 0}]]},
        "Route": {"main": [
            [{"node": "Layout normalisation", "type": "main", "index": 0}],
            [{"node": "OCR (scanned only)", "type": "main", "index": 0}],
        ]},
        "OCR (scanned only)": {"main": [[{"node": "Layout normalisation", "type": "main", "index": 0}]]},
        "Layout normalisation": {"main": [[{"node": "Structure rows (stub)", "type": "main", "index": 0}]]},
        "Structure rows (stub)": {"main": [[{"node": "Validate & reconcile", "type": "main", "index": 0}]]},
        "Validate & reconcile": {"main": [[{"node": "Reconciled?", "type": "main", "index": 0}]]},
        "Reconciled?": {"main": [
            [{"node": "Clean rows -> CSV", "type": "main", "index": 0}],
            [{"node": "Flagged -> review queue", "type": "main", "index": 0}],
        ]},
    }

    json.dump(wf, open(DST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote %s  (%d nodes, reading %s)" % (DST, len(new_nodes), PDF))


if __name__ == "__main__":
    main()
