# -*- coding: utf-8 -*-
"""一次性迁移：models_data.py (+ notes 合并) -> models/NNN.md
每个模型一个 Markdown 文件：frontmatter 写元数据，正文写博主讲解段落。
之后 build.py 直接读 models/，不再依赖 models_data.py。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models_data import MODELS

# 五根归属（与 gen_aurora.py 一致），用于给每个模型打 root 标签
ROOTS = [
  {"id": "think", "models": [8,10,11,12,13,14,15,16,17,18,21,24,29,30,38,61,62,71,74]},
  {"id": "do",    "models": [1,26,27,28,31,32,33,72,76,77]},
  {"id": "say",   "models": [2,3,4,5,6,7,9,22,23,25,39,43]},
  {"id": "lead",  "models": [20,34,35,36,37,40,41,42,44,45,46,47,63,64,65,66,67,68]},
  {"id": "grow",  "models": [19,48,49,50,51,52,53,54,55,56,57,58,59,60,69,70,73,75,78]},
]
n2root = {}
for r in ROOTS:
    for n in r["models"]:
        n2root[n] = r["id"]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(out, exist_ok=True)

count = 0
for m in MODELS:
    n = m["n"]
    root = n2root.get(n, "")
    fn = os.path.join(out, f"{n:03d}.md")
    L = []
    L.append("---")
    L.append(f"n: {n}")
    L.append(f"name: {m['name']}")
    L.append(f"cat: {m['cat']}")
    L.append(f"bv: {m['bv']}")
    L.append(f"vw: {m['vw']}")
    L.append(f"root: {root}")
    L.append(f"core: {m['core']}")
    L.append("pts:")
    for p in m.get("pts", []):
        L.append(f"  - {p}")
    L.append("sc:")
    for s in m.get("sc", []):
        L.append(f"  - {s}")
    L.append("---")
    L.append("")
    talk, case, quote, src, extra = (
        m.get("talk", ""), m.get("case", ""), m.get("quote", ""),
        m.get("src", ""), m.get("extra", ""))
    if talk:
        L += ["## 博主講解", talk, ""]
    if case:
        L += ["## 案例", case, ""]
    if quote:
        L += ["## 名言", quote, ""]
    if src:
        L += ["## 延伸學習", src, ""]
    if extra:
        L += ["## 實用提醒", extra, ""]
    with open(fn, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    count += 1

print(f"migrated {count} models -> {out}/")
