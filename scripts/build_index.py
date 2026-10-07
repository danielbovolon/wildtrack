#!/usr/bin/env python3
"""Rebuild data/index.json from the seed files.

Run after adding or changing files in data/seeds:
    python3 scripts/build_index.py
It also validates every file, and keeps only the newest 365 seeds
in the index (older files stay in the repo).
"""
import json, pathlib, sys, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CATS = {"sounddesign","music","field","synthesis","tools","film","games","art",
        "space","stage","radio","visual","design","nature","access","calls"}
KINDS = {"word","concept","quote","photo"}

def load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"Invalid JSON in {p}: {e}")

def check_seed(p, d):
    for k in ("key","label","seed"):
        if k not in d: sys.exit(f"{p.name}: missing '{k}'")
    sp = d["seed"]
    if not sp.get("text"): sys.exit(f"{p.name}: seed needs 'text'")
    if sp.get("kind") not in KINDS: sys.exit(f"{p.name}: seed kind '{sp.get('kind')}' must be one of {sorted(KINDS)}")
    if sp["kind"] == "quote" and not sp.get("by"): sys.exit(f"{p.name}: a quote needs 'by' (who said or wrote it)")
    if sp["kind"] == "photo":
        ph = sp.get("photo") or {}
        if not (ph.get("src") and ph.get("page")): sys.exit(f"{p.name}: a photo needs photo.src and photo.page (where it comes from)")
    elif not (sp.get("source") or {}).get("url"): sys.exit(f"{p.name}: seed needs source.url so it can be checked")
    ph = d.get("photo") or sp.get("photo") or {}
    if not (ph.get("src") and ph.get("page")): print(f"warning: {p.name} has no real photograph (photo.src + photo.page)")
    po = d.get("poem")
    if po:
        if not (po.get("text") and po.get("author")): sys.exit(f"{p.name}: a poem needs 'text' and 'author'")
        if not (po.get("source") or {}).get("url"): sys.exit(f"{p.name}: a poem needs source.url so it can be checked")
    elif d.get("key", "") >= "2026-10-08": print(f"warning: {p.name} has no poem")
    for i, it in enumerate(d.get("items", [])):
        for k in ("cat","title","url"):
            if k not in it: sys.exit(f"{p.name}: item {i} missing '{k}'")
        if it["cat"] not in CATS: print(f"warning: {p.name} item {i} has unknown category '{it['cat']}'")

seeds = []
for p in sorted((DATA / "seeds").glob("*.json"), reverse=True)[:365]:
    d = load(p); check_seed(p, d); seeds.append(p.name)

index = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
         "seeds": seeds}
(DATA / "index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
print(f"index.json: {len(seeds)} seeds")
