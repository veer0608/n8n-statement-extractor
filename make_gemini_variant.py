"""
Produce workflow.gemini.json - headless edges (so `n8n execute` can drive it)
plus the REAL LLM chain, pointed at Google Gemini.

Why Gemini and not Groq for this test: Groq's free tier has a hard
tokens-per-day ceiling that appears in no response header, so a run can die
halfway with nothing to show. Gemini's free tier has no equivalent silent
cliff, and there is already a live key on this machine.

workflow.json (the shipping copy) stays on OpenAI - that is what most buyers
have wired up already.
"""
import json

SRC = "workflow.test.json"      # headless trigger + file read already in place
FULL = "workflow.json"          # source of the real LLM nodes
DST = "workflow.gemini.json"

test = json.load(open(SRC, encoding="utf-8"))
full = json.load(open(FULL, encoding="utf-8"))
fnodes = {n["name"]: n for n in full["nodes"]}

# drop the stub, keep everything else
nodes = [n for n in test["nodes"] if n["name"] != "Structure rows (stub)"]

chain = json.loads(json.dumps(fnodes["Structure rows (LLM)"]))
parser = json.loads(json.dumps(fnodes["Structured Output Parser"]))

model = {
    "parameters": {
        "modelName": "models/gemini-2.5-flash",
        "options": {"temperature": 0},
    },
    "id": "gemini-model",
    "name": "Chat Model",
    "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
    "typeVersion": 1,
    "position": [700, 500],
}

nodes += [chain, model, parser]

test["nodes"] = nodes
test["id"] = "stmtExtractGemini"
test["name"] = "Statement Extractor (headless, Gemini)"

conns = test["connections"]
conns["Layout normalisation"] = {
    "main": [[{"node": "Structure rows (LLM)", "type": "main", "index": 0}]]}
conns["Structure rows (LLM)"] = {
    "main": [[{"node": "Validate & reconcile", "type": "main", "index": 0}]]}
conns.pop("Structure rows (stub)", None)
conns["Chat Model"] = {"ai_languageModel": [
    [{"node": "Structure rows (LLM)", "type": "ai_languageModel", "index": 0}]]}
conns["Structured Output Parser"] = {"ai_outputParser": [
    [{"node": "Structure rows (LLM)", "type": "ai_outputParser", "index": 0}]]}

json.dump(test, open(DST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("wrote %s  (%d nodes, model %s)"
      % (DST, len(nodes), model["parameters"]["modelName"]))
print("credential still has to be created in the n8n UI, then attached by id.")
