"""
Build the buyer zip in one step, so it can never ship a stale or
path-leaking workflow again.

Does, in order:
  1. regenerate the variants from workflow.json (make_*_variant.py)
  2. copy the shipping files into dist/
  3. strip any absolute machine path out of the copied workflows
     (make_test/gemini_variant.py bake in an absolute demo-PDF path)
  4. refuse to build if any secret or home path survives the scrub
  5. zip dist/ into statement-extractor-n8n.zip

Run it after ANY change to the workflows:

    python build_dist.py
"""
import json
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
ZIP = os.path.join(HERE, "statement-extractor-n8n.zip")

# Files that go to the buyer. SETUP.md already lives in dist/ and is hand-edited;
# everything else is copied fresh from the repo root each build.
FROM_ROOT = ["workflow.json", "workflow.gemini.json", "workflow.test.json", "demo_statement.pdf"]
IN_ZIP = ["SETUP.md"] + FROM_ROOT

# Anything matching these must NOT appear in a shipped file.
FORBIDDEN = re.compile(
    r"C:[\\/]Users|/home/|veera|schemablind|agentops|"
    r"gsk_|sk-[A-Za-z0-9]|AIza[0-9A-Za-z_-]{10}|GEMINI_API|GOOGLE_API",
    re.I)


def step(msg):
    print("• " + msg)


# 1. regenerate variants -----------------------------------------------------
for gen in ("make_test_variant.py", "make_gemini_variant.py"):
    r = subprocess.run([sys.executable, gen], cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("FAILED: %s\n%s" % (gen, r.stderr))
step("regenerated variants")

# 2. copy shipping files into dist/ ------------------------------------------
os.makedirs(DIST, exist_ok=True)
if not os.path.exists(os.path.join(DIST, "SETUP.md")):
    sys.exit("dist/SETUP.md is missing - it is the hand-written buyer guide, not generated.")
for f in FROM_ROOT:
    src, dst = os.path.join(HERE, f), os.path.join(DIST, f)
    with open(src, "rb") as a, open(dst, "wb") as b:
        b.write(a.read())
step("copied %d files into dist/" % len(FROM_ROOT))

# 3. strip absolute paths from the copied workflows --------------------------
for f in ("workflow.test.json", "workflow.gemini.json"):
    path = os.path.join(DIST, f)
    w = json.load(open(path, encoding="utf-8"))
    changed = False
    for n in w["nodes"]:
        p = n.get("parameters", {})
        fs = p.get("fileSelector", "")
        if isinstance(fs, str) and (fs.startswith("C:") or fs.startswith("/")):
            p["fileSelector"] = "demo_statement.pdf"
            changed = True
    if changed:
        json.dump(w, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
step("relativised absolute paths in dist workflows")

# 4. refuse to build if anything sensitive survived --------------------------
dirty = []
for f in IN_ZIP:
    path = os.path.join(DIST, f)
    if f.endswith(".pdf"):
        continue  # binary; the demo PDF is synthetic and already vetted
    text = open(path, encoding="utf-8", errors="replace").read()
    for m in FORBIDDEN.finditer(text):
        dirty.append("%s: %s" % (f, m.group(0)))
if dirty:
    print("\nREFUSING TO BUILD - sensitive strings found:")
    for d in dirty:
        print("  " + d)
    sys.exit(1)
step("scrub clean - no paths, usernames, or keys")

# 5. zip ---------------------------------------------------------------------
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for f in IN_ZIP:
        z.write(os.path.join(DIST, f), "statement-extractor/" + f)
step("built %s" % os.path.basename(ZIP))

with zipfile.ZipFile(ZIP) as z:
    print("\ncontents:")
    for i in z.infolist():
        print("  %7d  %s" % (i.file_size, i.filename))
