# -*- coding: utf-8 -*-
"""build.py —— 思维模型手册生成器（可迭代版）
数据单一事实源：models/NNN.md（frontmatter + 正文讲解）
渲染：Sprig 风格单文件 HTML（port 自 gen_aurora.py）

用法：
  python build.py            # 一次性构建 -> 思维模型手册.html + site/index.html
  python build.py --watch    # 监听 models/ 与 build.py，改动即重建
  python build.py --md       # 额外导出 思维模型手册.md
  python build.py --watch --md

依赖：仅 Python 标准库（零第三方依赖，便于持续迭代）
"""
import json, os, sys, glob, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(HERE, "models")
HTML_PATH = os.path.join(HERE, "思维模型手册.html")
SITE_DIR = os.path.join(HERE, "site")
SITE_PATH = os.path.join(SITE_DIR, "index.html")
MD_PATH = os.path.join(HERE, "思维模型手册.md")

CAT_ORDER = ["溝通表達", "學習成長", "目標與執行", "分析與思考", "管理與領導", "會議協作", "職業規劃", "決策判斷", "人才與組織", "財富與人生", "效率呈現"]

CAT_ICONS = {"溝通表達": "COMMUNICATE", "學習成長": "LEARN & GROW", "目標與執行": "GOAL & EXECUTE",
             "分析與思考": "THINK & ANALYZE", "管理與領導": "LEAD & MANAGE", "會議協作": "MEET & CO-CREATE",
             "職業規劃": "CAREER MAP", "決策判斷": "DECIDE WISE", "人才與組織": "PEOPLE & ORG",
             "財富與人生": "WEALTH & LIFE", "效率呈現": "PRESENT FAST"}

# 五根（core 为"核心模型"编号；models 列表在构建时按每个模型的 root 字段自动推导）
ROOTS = [
  {"id":"think","name":"想清楚","en":"THINK CLEAR","desc":"拆解問題、搞懂因果",
   "core":[21,38,17,8]},
  {"id":"do","name":"做到位","en":"EXECUTE WELL","desc":"目標→行動→反饋的閉環",
   "core":[1,32,33,72]},
  {"id":"say","name":"說得好","en":"COMMUNICATE","desc":"先結論、再結構、帶同理心",
   "core":[2,5,6,39]},
  {"id":"lead","name":"帶得動","en":"LEAD & COACH","desc":"對齊目標、移除干擾、把人當種子",
   "core":[34,35,37,44]},
  {"id":"grow","name":"走得遠","en":"CAREER & LIFE","desc":"你想成為誰，就把時間投給誰",
   "core":[57,53,70,50]},
]
CORE_SET = {c for r in ROOTS for c in r["core"]}

# 默认 GitHub 仓库（页面设置可覆盖；token 由用户在本机浏览器填写，不入库）
REPO_DEFAULT = {"owner": "Lester8-l", "repo": "mind-models", "branch": "main"}


# ============ 读取 models/*.md ============
def parse_md(text):
    """极简 frontmatter + 正文解析（零依赖，格式可控）。"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        fm = text[3:end].strip("\n")
        body = text[end + 4:]
    else:
        fm, body = "", text

    meta = {}
    list_key = None
    for line in fm.split("\n"):
        s = line.rstrip()
        if s[:2] in ("- ", "  -") or s == "-":
            item = s.lstrip("- ").strip()
            if list_key:
                meta.setdefault(list_key, []).append(item)
            continue
        if ":" in s:
            k, v = s.split(":", 1)
            k, v = k.strip(), v.strip()
            if v == "":
                list_key = k
                meta[list_key] = []
            else:
                list_key = None
                meta[k] = v

    meta["n"] = int(meta.get("n", 0))
    meta["vw"] = int(meta.get("vw", 0))

    sections, cur = {}, None
    for line in body.split("\n"):
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)

    def g(name):
        return "\n".join(sections.get(name, [])).strip()

    return {
        "n": meta["n"], "name": meta.get("name", ""), "cat": meta.get("cat", ""),
        "bv": meta.get("bv", ""), "vw": meta.get("vw", 0), "root": meta.get("root", ""),
        "core": meta.get("core", ""),
        "pts": meta.get("pts", []) or [], "sc": meta.get("sc", []) or [],
        "talk": g("博主講解"), "case": g("案例"), "quote": g("名言"),
        "src": g("延伸學習"), "extra": g("實用提醒"),
        "is_core": str(meta.get("is_core","")).strip().lower() in ("true","1","yes"),
    }


def load_models():
    models = []
    for fp in sorted(glob.glob(os.path.join(MODELS_DIR, "*.md"))):
        with open(fp, encoding="utf-8") as f:
            m = parse_md(f.read())
        if m["n"] == 0:
            continue
        if not m["root"]:
            print(f"[warn] {os.path.basename(fp)} 缺少 root，归类到未定义")
        m["is_core"] = m.get("is_core") or (m["n"] in CORE_SET)
        models.append(m)
    models.sort(key=lambda x: x["n"])
    return models


# ============ HTML 模板（port 自 gen_aurora.py）============
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>100個思維模型 · 檀東東Tango</title>
<style>
:root{
  --ink:#0b2330; --bone:#faf9f8; --obsidian:#141312; --espresso:#272420;
  --ash:#f3f3f3; --mist:#e8e7e6; --vapor:#dddcd9; --pebble:#c4c4bc;
  --fog:#9a9a91; --slate:#575653; --graphite:#6e6d6a; --coffee:#322e2a;
  --dusk:#efdcb6; --ember:#eba370; --twilight:#7d7a8f;
  --sunset:linear-gradient(135deg,rgb(239,220,182) 0%,rgb(235,163,126) 48%,rgb(125,122,143) 100%);
  --font-ui:'Inter','TT Commons Pro',ui-sans-serif,system-ui,-apple-system,'PingFang TC','Microsoft JhengHei','Noto Sans TC',sans-serif;
  --font-edit:'Inter','ABC Diatype',ui-sans-serif,system-ui,-apple-system,'PingFang TC','Microsoft JhengHei','Noto Sans TC',sans-serif;
  --radius-pill:32px; --radius-card:32px; --radius-badge:4px; --radius-hero:100px;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bone);color:var(--slate);font-family:var(--font-ui);line-height:1.5;font-weight:400}
::selection{background:rgba(235,163,126,.3)}
.wrap{max-width:1200px;margin:0 auto;padding:0 32px}
@media(max-width:720px){.wrap{padding:0 20px}}

/* ===== ANNOUNCE ===== */
.announce{background:var(--espresso);color:var(--bone);text-align:center;font-size:14px;padding:12px 16px;letter-spacing:.02em}

/* ===== NAV ===== */
nav{background:var(--bone);border-bottom:1px solid var(--mist)}
nav .wrap{display:flex;align-items:center;height:72px;gap:32px}
.brand{display:flex;align-items:center;gap:10px;color:var(--ink);text-decoration:none;font-family:var(--font-edit);font-size:18px;font-weight:500}
.brand .dot{width:10px;height:10px;border-radius:50%;background:var(--sunset);display:inline-block}
.nav-links{display:flex;gap:24px;margin-left:8px;flex:1;overflow-x:auto;scrollbar-width:none}
.nav-links::-webkit-scrollbar{display:none}
.nav-links a{color:var(--slate);text-decoration:none;font-size:16px;white-space:nowrap;transition:color .2s}
.nav-links a:hover{color:var(--ink)}
.nav-cta{margin-left:auto}
.btn-pill{background:var(--espresso);color:var(--bone);border:none;border-radius:var(--radius-pill);padding:12px 24px;font-size:16px;font-family:var(--font-ui);font-weight:400;cursor:pointer;transition:transform .2s,background .2s;display:inline-flex;align-items:center;gap:8px;text-decoration:none}
.btn-pill:hover{background:var(--coffee)}
.btn-pill:active{transform:scale(.98)}
.btn-ghost{background:transparent;color:var(--ink);border:1px solid var(--vapor);border-radius:var(--radius-pill);padding:11px 24px;font-size:16px;font-family:var(--font-ui);font-weight:400;cursor:pointer;transition:border-color .2s,background .2s;display:inline-flex;align-items:center;gap:8px;text-decoration:none}
.btn-ghost:hover{border-color:var(--ink);background:var(--ash)}

/* ===== HERO ===== */
.hero{padding:88px 0 80px}
.hero-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:64px;align-items:center}
.eyebrow{font-size:14px;color:var(--graphite);margin-bottom:24px;display:flex;align-items:center;gap:12px}
.eyebrow::before{content:"";width:40px;height:1px;background:var(--pebble)}
.hero h1{font-size:clamp(40px,5.6vw,64px);font-weight:500;line-height:1.2;letter-spacing:-.01em;color:var(--obsidian);font-family:var(--font-edit)}
.hero .sub{margin-top:24px;font-size:18px;color:var(--slate);max-width:560px;line-height:1.5}
.hero-actions{display:flex;gap:16px;margin-top:40px;flex-wrap:wrap}
.hero-card{border-radius:var(--radius-hero);background:var(--sunset);padding:56px 48px;min-height:340px;display:flex;flex-direction:column;justify-content:center;gap:8px}
.hero-card .hc-label{font-size:14px;color:rgba(11,35,48,.6);margin-top:16px}
.hero-card .hc-num{font-size:clamp(48px,6vw,72px);font-weight:500;line-height:1.1;letter-spacing:-.02em;color:var(--obsidian);font-family:var(--font-edit)}
.hero-card .hc-row{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:8px}
.hero-card .hc-mini .n{font-size:32px;font-weight:500;color:var(--obsidian);font-family:var(--font-edit);line-height:1.1}
.hero-card .hc-mini .l{font-size:14px;color:rgba(11,35,48,.6);margin-top:4px}

/* ===== CAT BAR ===== */
.cat-bar{position:sticky;top:0;z-index:90;background:rgba(250,249,248,.95);backdrop-filter:blur(10px);padding:14px 0;border-bottom:1px solid var(--mist)}
.cat-bar .wrap{display:flex;gap:8px;flex-wrap:wrap}
.cat-chip{font-size:15px;color:var(--slate);background:transparent;border:1px solid var(--vapor);border-radius:var(--radius-pill);padding:8px 18px;cursor:pointer;transition:.2s;font-family:var(--font-ui);white-space:nowrap}
.cat-chip:hover{color:var(--ink);border-color:var(--ink)}
.cat-chip.on{background:var(--ink);color:var(--bone);border-color:var(--ink)}

/* ===== SECTION / SEARCH ===== */
.section{scroll-margin-top:70px}
.section-head{display:flex;align-items:baseline;gap:16px;margin:64px 0 8px}
.section-head h2{font-size:32px;font-weight:500;line-height:1.2;color:var(--obsidian);font-family:var(--font-edit)}
.section-head .count{font-size:14px;color:var(--pebble)}
.search-row{display:flex;gap:16px;align-items:center;margin:32px 0 28px}
.search-box{flex:1;display:flex;align-items:center;gap:12px;background:var(--ash);border:1px solid var(--mist);border-radius:var(--radius-pill);padding:13px 22px;transition:border-color .2s}
.search-box:focus-within{border-color:var(--ink)}
.search-box svg{flex:none;opacity:.45}
.search-box input{flex:1;background:none;border:none;outline:none;color:var(--ink);font-size:16px;font-family:var(--font-ui)}
.search-box input::placeholder{color:var(--fog)}
.result-count{font-size:14px;color:var(--pebble);white-space:nowrap}

/* ===== CARDS ===== */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:24px;padding-bottom:96px}
.card{background:var(--ash);border-radius:var(--radius-card);padding:40px 36px;cursor:pointer;transition:background .25s,transform .25s;display:flex;flex-direction:column;gap:14px;position:relative;border:1px solid transparent}
.card:hover{background:#ecebe9;transform:translateY(-2px)}
.card:active{transform:translateY(-1px)}
.card-top{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--pebble);flex-wrap:wrap}
.card-top .no{font-family:var(--font-edit);color:var(--graphite)}
.card-top .cat{background:var(--bone);color:var(--slate);border-radius:var(--radius-badge);padding:2px 10px;font-size:13px}
.card-top .vw{margin-left:auto;color:var(--fog)}
.root-tag{background:var(--ink);color:var(--bone);border-radius:var(--radius-badge);padding:2px 10px;font-size:12px;font-weight:500;white-space:nowrap}
.core-badge{background:var(--ember);color:var(--obsidian);border-radius:var(--radius-badge);padding:2px 8px;font-size:11px;font-weight:500;white-space:nowrap}
.card h3{font-size:22px;font-weight:500;line-height:1.3;color:var(--obsidian);font-family:var(--font-edit);letter-spacing:-.01em}
.card .core{font-size:15px;color:var(--slate);line-height:1.6}
.card .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto}
.chip{font-size:13px;color:var(--ink);background:var(--bone);border-radius:var(--radius-pill);padding:4px 12px}
.card .arrow{position:absolute;right:28px;bottom:28px;width:36px;height:36px;border-radius:50%;background:var(--bone);display:flex;align-items:center;justify-content:center;color:var(--ink);font-size:14px;transition:background .2s}
.card:hover .arrow{background:#fff}
.card .talk-hint{margin-top:2px;font-size:13px;color:var(--fog)}

/* ===== DETAIL ===== */
.detail{position:fixed;inset:0;z-index:200;background:var(--bone);overflow-y:auto;display:none}
.detail.open{display:block}
.detail-bar{position:sticky;top:0;z-index:10;background:rgba(250,249,248,.95);backdrop-filter:blur(10px);border-bottom:1px solid var(--mist)}
.detail-bar .wrap{display:flex;align-items:center;height:72px;gap:20px}
.back-btn{display:flex;align-items:center;gap:8px;background:transparent;border:1px solid var(--vapor);color:var(--ink);border-radius:var(--radius-pill);padding:10px 20px;font-size:15px;cursor:pointer;font-family:var(--font-ui);transition:.2s}
.back-btn:hover{border-color:var(--ink)}
.detail-bar .crumb{font-size:15px;color:var(--fog)}
.detail-body{padding:72px 32px 120px;max-width:860px}
.d-top{display:flex;align-items:center;gap:10px;font-size:14px;color:var(--pebble);margin-bottom:20px}
.d-top .no{color:var(--graphite)}
.d-top .cat{background:var(--ash);color:var(--ink);border-radius:var(--radius-badge);padding:3px 12px}
.d-title{font-size:clamp(36px,5vw,48px);font-weight:500;line-height:1.2;letter-spacing:-.01em;color:var(--obsidian);font-family:var(--font-edit);margin-bottom:32px}
.d-meta{display:flex;align-items:center;gap:48px;flex-wrap:wrap;padding-bottom:40px;border-bottom:1px solid var(--mist);margin-bottom:48px}
.d-meta .vw b{font-size:clamp(28px,3.5vw,40px);font-weight:500;color:var(--ink);letter-spacing:-.01em;display:block;line-height:1.1;font-family:var(--font-edit)}
.d-meta .vw span{font-size:14px;color:var(--pebble);display:block;margin-top:6px}
.d-meta .btn{margin-left:auto}
.d-sec{margin-bottom:48px}
.d-sec h4{font-size:14px;color:var(--graphite);margin-bottom:16px;font-weight:400;letter-spacing:.02em}
.d-core{font-size:18px;line-height:1.6;color:var(--ink);max-width:760px;font-family:var(--font-edit)}
.d-pts{list-style:none;display:flex;flex-direction:column;gap:12px;max-width:760px}
.d-pts li{font-size:16px;color:var(--slate);padding-left:28px;position:relative;line-height:1.6}
.d-pts li::before{content:"";position:absolute;left:4px;top:10px;width:9px;height:9px;border-radius:3px;background:var(--ember)}
.d-chips{display:flex;flex-wrap:wrap;gap:8px}
.d-talk{background:var(--ash);border-radius:var(--radius-card);padding:48px}
.d-talk .tp{font-size:16px;line-height:1.9;color:var(--ink);max-width:760px}
.d-talk .tc{margin-top:24px;font-size:15px;line-height:1.8;color:var(--slate);max-width:760px}
.d-talk .tc b{color:var(--ink);font-weight:500;margin-right:10px;font-size:14px}
.d-talk .tq{margin-top:24px;font-size:17px;color:var(--coffee);line-height:1.8;padding-left:18px;border-left:2px solid var(--ember);max-width:760px;font-family:var(--font-edit)}
.d-talk .ts{margin-top:24px;font-size:14px;color:var(--graphite);line-height:1.7;max-width:760px}
.d-talk .ts b{color:var(--ink);font-weight:500;margin-right:8px;font-size:14px}
.d-talk .te{margin-top:24px;font-size:14px;color:var(--slate);background:var(--bone);border:1px solid var(--mist);border-radius:12px;padding:16px 22px;line-height:1.8;max-width:760px}
.d-nav{display:flex;gap:16px;margin-top:72px;padding-top:40px;border-top:1px solid var(--mist)}
.d-nav a{flex:1;background:var(--ash);border-radius:var(--radius-card);padding:28px 32px;text-decoration:none;transition:background .2s}
.d-nav a:hover{background:#ecebe9}
.d-nav .dir{font-size:13px;color:var(--pebble);display:block;margin-bottom:8px}
.d-nav .nm{font-size:18px;font-weight:500;color:var(--obsidian);font-family:var(--font-edit)}
.d-nav a.next{text-align:right}

/* ===== CTA / FOOTER ===== */
.cta{margin:40px 0 96px}
.cta-card{background:var(--espresso);border-radius:var(--radius-hero);padding:96px 64px;text-align:left}
.cta-card .big{font-size:clamp(32px,4.5vw,48px);font-weight:500;line-height:1.2;letter-spacing:-.01em;color:var(--bone);font-family:var(--font-edit);max-width:640px}
.cta-card .big .hl{color:var(--dusk)}
.cta-card .f-sub{margin-top:20px;font-size:16px;color:rgba(250,249,248,.7);max-width:560px;line-height:1.6}
.cta-card .f-cta{margin-top:36px;display:flex;gap:16px;flex-wrap:wrap}
.cta-card .btn-pill{background:var(--bone);color:var(--espresso)}
.cta-card .btn-pill:hover{background:var(--dusk)}
.cta-card .btn-ghost{border-color:rgba(250,249,248,.4);color:var(--bone)}
.cta-card .btn-ghost:hover{border-color:var(--bone);background:rgba(250,249,248,.08)}
.cta-card .f-meta{margin-top:72px;padding-top:32px;border-top:1px solid rgba(250,249,248,.15);font-size:13px;color:rgba(250,249,248,.55);display:flex;gap:24px;flex-wrap:wrap}
.cta-card .f-meta a{color:rgba(250,249,248,.75);text-decoration:none}
.cta-card .f-meta a:hover{color:var(--bone)}

@media(max-width:860px){
  .hero-grid{grid-template-columns:1fr;gap:40px}
  .hero-card{min-height:auto;padding:48px 36px}
  .detail-body{padding:48px 20px 96px}
  .d-talk{padding:32px 24px}
  .cta-card{padding:64px 32px}
  .d-meta{gap:24px}
}

/* ===== EDIT / GITHUB ===== */
.edit-btn{position:absolute;right:28px;top:28px;width:34px;height:34px;border-radius:50%;background:var(--bone);border:1px solid var(--vapor);color:var(--slate);font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .2s,border-color .2s;z-index:5}
.card:hover .edit-btn{opacity:1}
.edit-btn:hover{border-color:var(--ink);color:var(--ink)}
.nav-tools{display:flex;align-items:center;gap:10px;margin-left:auto}
.btn-mini{background:transparent;color:var(--ink);border:1px solid var(--vapor);border-radius:var(--radius-pill);padding:9px 16px;font-size:14px;font-family:var(--font-ui);cursor:pointer;transition:.2s;display:inline-flex;align-items:center;gap:6px;text-decoration:none}
.btn-mini:hover{border-color:var(--ink);background:var(--ash)}
.btn-mini.solid{background:var(--espresso);color:var(--bone);border-color:var(--espresso)}
.btn-mini.solid:hover{background:var(--coffee)}

/* modal */
.modal{position:fixed;inset:0;z-index:300;background:rgba(20,19,18,.45);backdrop-filter:blur(2px);display:none;align-items:flex-start;justify-content:center;padding:48px 20px;overflow-y:auto}
.modal.open{display:flex}
.modal-card{background:var(--bone);border-radius:var(--radius-card);max-width:720px;width:100%;padding:40px 40px 32px;box-shadow:0 30px 80px rgba(20,19,18,.25)}
.modal-card h3{font-size:24px;font-weight:500;color:var(--obsidian);font-family:var(--font-edit);margin-bottom:4px}
.modal-card .m-sub{font-size:14px;color:var(--pebble);margin-bottom:24px}
.field{margin-bottom:18px}
.field label{display:block;font-size:13px;color:var(--graphite);margin-bottom:6px;font-family:var(--font-edit)}
.field .row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.field input,.field select,.field textarea{width:100%;background:var(--ash);border:1px solid var(--mist);border-radius:14px;padding:11px 14px;color:var(--ink);font-size:15px;font-family:var(--font-ui);outline:none;transition:border-color .2s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--ink)}
.field textarea{resize:vertical;min-height:84px;line-height:1.6}
.field .hint{font-size:12px;color:var(--fog);margin-top:5px}
.modal-foot{display:flex;gap:12px;justify-content:flex-end;margin-top:8px;padding-top:20px;border-top:1px solid var(--mist)}
.checkbox-row{display:flex;align-items:center;gap:10px}
.checkbox-row input{width:18px;height:18px;accent-color:var(--espresso)}

/* toast */
.toast{position:fixed;left:50%;bottom:40px;transform:translateX(-50%) translateY(20px);background:var(--obsidian);color:var(--bone);padding:14px 24px;border-radius:var(--radius-pill);font-size:15px;z-index:400;opacity:0;transition:opacity .25s,transform .25s;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.toast.err{background:#9b2c2c}
</style>
</head>
<body>

<div class="announce">合集 78 支視頻 · 基於語音轉寫稿提煉 · 點擊卡片查看詳情</div>

<nav>
  <div class="wrap">
    <a class="brand" href="#top"><span class="dot"></span>TANGO · 100 MODELS</a>
    <div class="nav-links" id="navLinks"></div>
    <div class="nav-tools">
      <button class="btn-mini" onclick="openSettings()" title="GitHub 設定">⚙ 設定</button>
      <button class="btn-mini solid" onclick="openEditor(0)">＋ 新增模型</button>
      <button class="btn-pill" onclick="randomModel()">隨機模型</button>
    </div>
  </div>
</nav>

<header class="hero" id="top">
  <div class="wrap hero-grid">
    <div>
      <div class="eyebrow">TANGO × THINKING MODELS · 2022–2023</div>
      <h1>100個思維模型<br>一本暖紙筆記</h1>
      <p class="sub">UP主「檀東東Tango」的思維模型系列合集：每個模型都是一把解決特定場景問題的鑰匙。本手冊基於全部 78 支視頻的語音轉寫稿提煉而成，點擊卡片可進入詳情。</p>
      <div class="hero-actions">
        <button class="btn-pill" onclick="document.getElementById('cards').scrollIntoView()">探索全部模型</button>
        <a class="btn-ghost" href="https://space.bilibili.com/14739873/lists/437530?type=season" target="_blank">前往B站合集</a>
      </div>
    </div>
    <div class="hero-card">
      <div class="hc-label">合集總覽</div>
      <div class="hc-num">78</div>
      <div class="hc-label">思維模型 · 一一對應</div>
      <div class="hc-row">
        <div class="hc-mini"><div class="n">5</div><div class="l">根模型</div></div>
        <div class="hc-mini"><div class="n">__VIEWS__</div><div class="l">合計播放</div></div>
        <div class="hc-mini"><div class="n">78</div><div class="l">博主講解</div></div>
      </div>
    </div>
  </div>
</header>

<div class="cat-bar" id="catBar">
  <div class="wrap" id="catChips"></div>
</div>

<section class="section" id="cards">
  <div class="wrap">
    <div class="section-head" id="sectionHead" style="margin-top:48px">
      <h2>模型庫</h2><span class="count" id="resultCount"></span>
    </div>
    <div class="search-row">
      <div class="search-box">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9a9a91" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        <input id="searchInput" type="text" placeholder="搜尋模型名稱、場景、關鍵字…">
      </div>
      <div class="result-count" id="resultCount2"></div>
    </div>
    <div class="grid" id="grid"></div>
  </div>
</section>

<div class="cta">
  <div class="wrap">
    <div class="cta-card">
      <div class="big">把每一把鑰匙<br>都用在自己的<span class="hl">生活裡</span></div>
      <p class="f-sub">「有用是因為有用」——學一個模型，多一把鑰匙。道阻且長，一起收穫更多的解題鑰匙。</p>
      <div class="f-cta">
        <button class="btn-pill" onclick="randomModel()">隨機打開一個模型</button>
        <a class="btn-ghost" href="https://space.bilibili.com/14739873/lists/437530?type=season" target="_blank">前往B站合集</a>
      </div>
      <div class="f-meta">
        <span>數據來源：<a href="https://space.bilibili.com/14739873/lists/437530?type=season" target="_blank">B站合集 · 100個思維模型（檀東東Tango）</a></span>
        <span>合集 78 支視頻：No.001-075 單模型 + No.076-078 合輯</span>
        <span>特別篇（33面試技巧/被罵2年）非模型，未收錄</span>
        <span>博主講解基於語音轉寫稿提煉，細節以原視頻為準</span>
      </div>
    </div>
  </div>
</div>

<div class="detail" id="detail">
  <div class="detail-bar">
    <div class="wrap">
      <button class="back-btn" onclick="closeDetail()">← 返回</button>
      <div class="crumb" id="dCrumb"></div>
      <button class="btn-mini" style="margin-left:auto" onclick="openEditor(currentDetailN)" title="編輯本模型">✎ 編輯</button>
    </div>
  </div>
  <div class="detail-body" id="detailBody"></div>
</div>

<!-- ===== 編輯器 / 設定 彈窗 ===== -->
<div class="modal" id="editorModal">
  <div class="modal-card">
    <h3 id="editorTitle">編輯模型</h3>
    <p class="m-sub" id="editorSub">改完點「保存」→ 直接寫回 GitHub 的 models/*.md</p>
    <div class="field"><div class="row2">
      <div><label>編號 n（新增時自動）</label><input id="f_n" type="number" min="1"></div>
      <div><label>模型名稱</label><input id="f_name" placeholder="如 PREP"></div>
    </div></div>
    <div class="field"><div class="row2">
      <div><label>分類</label><select id="f_cat"></select></div>
      <div><label>所屬根</label><select id="f_root"></select></div>
    </div></div>
    <div class="field"><div class="row2">
      <div><label>BV 號（B站視頻）</label><input id="f_bv" placeholder="BV1xxxxxx"></div>
      <div><label>播放量（可留空）</label><input id="f_vw" type="number" min="0"></div>
    </div></div>
    <div class="field">
      <label>核心思想（一句話）</label>
      <textarea id="f_core" rows="2"></textarea>
    </div>
    <div class="field">
      <label>關鍵要點（每行一條）</label>
      <textarea id="f_pts" rows="4" placeholder="要點1&#10;要點2&#10;要點3"></textarea>
    </div>
    <div class="field">
      <label>適用場景（每行一條）</label>
      <textarea id="f_sc" rows="3" placeholder="場景1&#10;場景2"></textarea>
    </div>
    <div class="field">
      <label>博主講解（正文）</label>
      <textarea id="f_talk" rows="5"></textarea>
    </div>
    <div class="field"><div class="row2">
      <div><label>案例</label><textarea id="f_case" rows="3"></textarea></div>
      <div><label>金句</label><textarea id="f_quote" rows="3"></textarea></div>
    </div></div>
    <div class="field"><div class="row2">
      <div><label>延伸學習</label><textarea id="f_src" rows="3"></textarea></div>
      <div><label>實用提醒</label><textarea id="f_extra" rows="3"></textarea></div>
    </div></div>
    <div class="field checkbox-row">
      <input id="f_core_flag" type="checkbox"><label for="f_core_flag" style="margin:0">標記為「核心模型」（顯示核心徽章）</label>
    </div>
    <div class="modal-foot">
      <button class="btn-ghost" onclick="closeEditor()">取消</button>
      <button class="btn-pill" id="saveBtn" onclick="saveEditor()">保存到 GitHub ↗</button>
    </div>
  </div>
</div>

<div class="modal" id="settingsModal">
  <div class="modal-card">
    <h3>GitHub 連接</h3>
    <p class="m-sub">保存後：開啟頁面時自動從倉庫拉取最新 data.json；編輯模型會直接寫回 models/*.md。Token 只存在你瀏覽器本地。</p>
    <div class="field"><div class="row2">
      <div><label>Owner</label><input id="s_owner" placeholder="GitHub 用戶名"></div>
      <div><label>Repo</label><input id="s_repo" placeholder="倉庫名"></div>
    </div></div>
    <div class="field"><div class="row2">
      <div><label>Branch</label><input id="s_branch" placeholder="main"></div>
      <div><label>Token（可留空=只讀）</label><input id="s_token" type="password" placeholder="ghp_... 或 gho_..."></div>
    </div></div>
    <p class="m-sub" style="margin-top:0">Token 用於寫入：<a href="https://github.com/settings/tokens" target="_blank">GitHub → Settings → Developer settings → Personal access tokens</a>，勾選該倉庫的 Contents: Read &amp; Write 權限。</p>
    <div class="modal-foot">
      <button class="btn-ghost" onclick="closeSettings()">取消</button>
      <button class="btn-pill" onclick="saveSettings()">保存並連接</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const DATA = __DATA__;
const CAT_ICONS = __CAT_ICONS__;
const ROOTS = DATA.roots;
const REPO_DEFAULT = __REPO_DEFAULT__;

let currentRoot = "all";
let currentDetailN = 0;
const $ = s => document.querySelector(s);

/* 根导航 + 过滤chips */
function rootName(id){ const r = ROOTS.find(x=>x.id===id); return r?r.name:""; }
function renderCats(){
  const chips = document.getElementById("catChips");
  const items = [{id:"all",name:"全部"}, ...ROOTS.map(r=>({id:r.id,name:r.name}))];
  chips.innerHTML = items.map(it => `<button class="cat-chip${it.id===currentRoot?" on":""}" onclick="setRoot('${it.id}')">${it.name}</button>`).join("");
  const nav = document.getElementById("navLinks");
  nav.innerHTML = ROOTS.map(r => `<a href="#root-${r.id}" onclick="setRoot('${r.id}')">${r.name}</a>`).join("");
}
function setRoot(id){
  currentRoot = id;
  renderCats();
  renderGrid();
  const el = document.getElementById("cards");
  if(window.scrollY > 500) el.scrollIntoView({behavior:"smooth"});
}

/* 卡片网格 */
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function fmt(n){return n>=10000 ? (n/10000).toFixed(1).replace(/\.0$/,"")+"萬" : n.toLocaleString();}

function renderGrid(){
  const q = ($("#searchInput").value||"").trim().toLowerCase();
  const grid = document.getElementById("grid");
  let list = DATA.models;
  if(currentRoot !== "all") list = list.filter(m => m.root === currentRoot);
  if(q) list = list.filter(m => (m.name+m.core+(m.sc||[]).join(" ")+(m.talk||"")+(m.case||"")).toLowerCase().includes(q));
  grid.innerHTML = list.map(m => `
    <article class="card" onclick="openDetail(${m.n})">
      <button class="edit-btn" onclick="event.stopPropagation();openEditor(${m.n})" title="編輯">✎</button>
      <div class="card-top">
        <span class="no">No.${String(m.n).padStart(3,"0")}</span>
        <span class="root-tag">${rootName(m.root)}</span>
        <span class="cat">${esc(m.cat)}</span>
        ${m.is_core?'<span class="core-badge">核心</span>':''}
        <span class="vw">▶ ${fmt(m.vw)}</span>
      </div>
      <h3>${esc(m.name)}</h3>
      <p class="core">${esc(m.core)}</p>
      <div class="chips">${(m.sc||[]).slice(0,3).map(s=>`<span class="chip">${esc(s)}</span>`).join("")}</div>
      <div class="talk-hint">${m.talk ? "含博主講解" : ""}</div>
      <span class="arrow">↗</span>
    </article>`).join("");
  const n = list.length;
  $("#resultCount").textContent = `${n} / ${DATA.models.length} MODELS`;
  $("#resultCount2").textContent = `${n} 個模型`;
}

/* 详情页 */
function openDetail(n){
  const m = DATA.models.find(x => x.n === n);
  if(!m) return;
  currentDetailN = n;
  location.hash = "m" + String(n).padStart(3,"0");
  renderDetail(n);
}
function renderDetail(n){
  const m = DATA.models.find(x => x.n === n);
  if(!m) return;
  const d = document.getElementById("detail");
  const root = ROOTS.find(r => r.id === m.root);
  $("#dCrumb").textContent = `MODEL ${String(n).padStart(3,"0")} · ${root?root.name:""}`;
  const prev = DATA.models.find(x => x.n === n-1);
  const next = DATA.models.find(x => x.n === n+1);
  const siblings = root ? DATA.models.filter(x => x.root === m.root && x.n !== m.n) : [];
  const siblingsHtml = siblings.length ? `
    <div class="d-sec"><h4>同根模型 · ${root.name}</h4><div class="d-chips">${siblings.map(s=>`<span class="chip" style="cursor:pointer" onclick="openDetail(${s.n})">${esc(s.name)}</span>`).join("")}</div></div>` : "";
  const navHtml = `<div class="d-nav">
    ${prev?`<a href="#m${String(prev.n).padStart(3,"0")}" onclick="openDetail(${prev.n})"><span class="dir">← 上一個</span><span class="nm">No.${String(prev.n).padStart(3,"0")} ${esc(prev.name)}</span></a>`:"<a style='visibility:hidden'></a>"}
    ${next?`<a class="next" href="#m${String(next.n).padStart(3,"0")}" onclick="openDetail(${next.n})"><span class="dir">下一個 →</span><span class="nm">No.${String(next.n).padStart(3,"0")} ${esc(next.name)}</span></a>`:"<a style='visibility:hidden'></a>"}
  </div>`;
  $("#detailBody").innerHTML = `
    <div class="d-top"><span class="no">No.${String(n).padStart(3,"0")}</span><span class="root-tag">${rootName(m.root)}</span><span class="cat">${esc(m.cat)}</span>${m.is_core?'<span class="core-badge">核心</span>':''}</div>
    <h1 class="d-title">${esc(m.name)}</h1>
    <div class="d-meta">
      <div class="vw"><b>${fmt(m.vw)}</b><span>播放量</span></div>
      <div class="vw"><b>${(m.sc||[]).length}</b><span>適用場景</span></div>
      <a class="btn-pill btn" href="https://www.bilibili.com/video/${m.bv}" target="_blank">觀看原視頻 ↗</a>
    </div>
    <div class="d-sec"><h4>核心思想</h4><p class="d-core">${esc(m.core)}</p></div>
    <div class="d-sec"><h4>關鍵要點</h4><ul class="d-pts">${(m.pts||[]).map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>
    <div class="d-sec"><h4>適用場景</h4><div class="d-chips">${(m.sc||[]).map(s=>`<span class="chip">${esc(s)}</span>`).join("")}</div></div>
    ${m.talk?`
    <div class="d-sec"><h4>博主講解</h4>
      <div class="d-talk">
        <p class="tp">${esc(m.talk)}</p>
        ${m.case?`<p class="tc"><b>案例</b>${esc(m.case)}</p>`:""}
        ${m.quote?`<p class="tq">「${esc(m.quote)}」</p>`:""}
        ${m.src?`<p class="ts"><b>延伸學習</b>${esc(m.src)}</p>`:""}
        ${m.extra?`<p class="te"><b>實用提醒</b>${esc(m.extra)}</p>`:""}
      </div>
    </div>`:""}
    ${siblingsHtml}
    ${navHtml}
  `;
  d.classList.add("open");
  document.body.style.overflow = "hidden";
  d.scrollTop = 0;
}
function closeDetail(){
  location.hash = "";
}
function randomModel(){
  const n = DATA.models[Math.floor(Math.random()*DATA.models.length)].n;
  openDetail(n);
}

/* hash 路由 */
window.addEventListener("hashchange", () => {
  const h = location.hash.replace("#","");
  const d = document.getElementById("detail");
  if(h.startsWith("m") && /^m\d{3}$/.test(h)){
    renderDetail(parseInt(h.slice(1),10));
  } else {
    d.classList.remove("open");
    document.body.style.overflow = "";
    renderGrid();
  }
});

$("#searchInput").addEventListener("input", renderGrid);

/* ===== GitHub 編輯器 ===== */
const CAT_ORDER = __CAT_ORDER__;
function toast(msg, err){
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast show" + (err ? " err" : "");
  clearTimeout(t._tm);
  t._tm = setTimeout(()=> t.className = "toast", 3200);
}
function ghSettings(){
  try{ return JSON.parse(localStorage.getItem("mm_settings") || "null"); }catch(e){ return null; }
}
function saveGhSettings(s){ localStorage.setItem("mm_settings", JSON.stringify(s)); }
function b64u(str){ return btoa(unescape(encodeURIComponent(str))); }

async function fetchLive(){
  const s = ghSettings();
  if(!s || !s.owner || !s.repo) return false;
  const url = `https://raw.githubusercontent.com/${encodeURIComponent(s.owner)}/${encodeURIComponent(s.repo)}/${encodeURIComponent(s.branch||"main")}/data.json`;
  try{
    const r = await fetch(url, {cache:"no-store"});
    if(!r.ok) return false;
    const d = await r.json();
    if(d && Array.isArray(d.models) && d.models.length){
      DATA.models = d.models;
      if(d.roots) DATA.roots = d.roots;
      renderCats(); renderGrid();
      return true;
    }
  }catch(e){ console.warn("fetchLive:", e); }
  return false;
}

async function ghGetSha(path){
  const s = ghSettings();
  if(!s || !s.owner || !s.repo) return null;
  const headers = s.token ? {Authorization:"token "+s.token} : {};
  try{
    const r = await fetch(`https://api.github.com/repos/${s.owner}/${s.repo}/contents/${path}?ref=${encodeURIComponent(s.branch||"main")}`, {headers});
    if(r.ok){ const d = await r.json(); return d.sha || null; }
  }catch(e){}
  return null;
}
async function ghPutFile(path, content, message){
  const s = ghSettings();
  if(!s || !s.token){ toast("請先設定 GitHub Token（⚙ 設定）", true); openSettings(); return false; }
  const sha = await ghGetSha(path);
  const body = {message, content: b64u(content), branch: s.branch||"main"};
  if(sha) body.sha = sha;
  try{
    const r = await fetch(`https://api.github.com/repos/${s.owner}/${s.repo}/contents/${path}`, {
      method:"PUT",
      headers:{Authorization:"token "+s.token, "Content-Type":"application/json", "Accept":"application/vnd.github+json"},
      body: JSON.stringify(body)
    });
    if(!r.ok){
      const e = await r.json().catch(()=>({}));
      toast("GitHub 寫入失敗：" + (e.message || r.status), true);
      return false;
    }
    return true;
  }catch(e){
    toast("網絡錯誤：" + e.message, true);
    return false;
  }
}

function fillEditorSelects(){
  const catSel = $("#f_cat");
  catSel.innerHTML = CAT_ORDER.map(c => `<option>${esc(c)}</option>`).join("");
  const rootSel = $("#f_root");
  rootSel.innerHTML = ROOTS.map(r => `<option value="${r.id}">${esc(r.name)}</option>`).join("");
}
function openEditor(n){
  fillEditorSelects();
  const m = n ? DATA.models.find(x=>x.n===n) : null;
  $("#editorTitle").textContent = m ? `編輯 No.${String(m.n).padStart(3,"0")} ${m.name}` : "新增模型";
  $("#editorSub").textContent = m ? "改完點保存 → 直接寫回 GitHub 的 models/*.md" : "保存後會生成新的 models/NNN.md 並寫入 GitHub";
  $("#f_n").value = m ? m.n : (DATA.models.reduce((a,x)=>Math.max(a,x.n),0)+1);
  $("#f_name").value = m ? m.name : "";
  $("#f_cat").value = m ? m.cat : "";
  $("#f_root").value = m ? m.root : "";
  $("#f_bv").value = m ? m.bv : "";
  $("#f_vw").value = m ? m.vw : "";
  $("#f_core").value = m ? m.core : "";
  $("#f_pts").value = m ? (m.pts||[]).join("\n") : "";
  $("#f_sc").value = m ? (m.sc||[]).join("\n") : "";
  $("#f_talk").value = m ? m.talk : "";
  $("#f_case").value = m ? m.case : "";
  $("#f_quote").value = m ? m.quote : "";
  $("#f_src").value = m ? m.src : "";
  $("#f_extra").value = m ? m.extra : "";
  $("#f_core_flag").checked = m ? !!m.is_core : false;
  $("#editorModal").classList.add("open");
  document.body.style.overflow = "hidden";
  setTimeout(()=> $("#f_name").focus(), 60);
}
function closeEditor(){
  $("#editorModal").classList.remove("open");
  document.body.style.overflow = "";
}
function readForm(){
  const lines = v => v.split("\n").map(s=>s.trim()).filter(Boolean);
  return {
    n: parseInt($("#f_n").value,10) || 0,
    name: $("#f_name").value.trim(),
    cat: $("#f_cat").value,
    root: $("#f_root").value,
    bv: $("#f_bv").value.trim(),
    vw: parseInt($("#f_vw").value,10) || 0,
    core: $("#f_core").value.trim(),
    pts: lines($("#f_pts").value),
    sc: lines($("#f_sc").value),
    talk: $("#f_talk").value.trim(),
    case: $("#f_case").value.trim(),
    quote: $("#f_quote").value.trim(),
    src: $("#f_src").value.trim(),
    extra: $("#f_extra").value.trim(),
    is_core: $("#f_core_flag").checked
  };
}
function formToMd(f){
  const L = [];
  L.push("---");
  L.push("n: " + f.n);
  L.push("name: " + f.name);
  L.push("cat: " + f.cat);
  L.push("bv: " + f.bv);
  L.push("vw: " + f.vw);
  L.push("root: " + f.root);
  if(f.is_core) L.push("is_core: true");
  if(f.core) L.push("core: " + f.core.replace(/\s+/g," "));
  if(f.pts.length){ L.push("pts:"); f.pts.forEach(p=>L.push("- " + p)); }
  if(f.sc.length){ L.push("sc:"); f.sc.forEach(p=>L.push("- " + p)); }
  L.push("---");
  if(f.talk){ L.push("## 博主講解"); L.push(f.talk); }
  if(f.case){ L.push("## 案例"); L.push(f.case); }
  if(f.quote){ L.push("## 名言"); L.push(f.quote); }
  if(f.src){ L.push("## 延伸學習"); L.push(f.src); }
  if(f.extra){ L.push("## 實用提醒"); L.push(f.extra); }
  return L.join("\n") + "\n";
}
async function saveEditor(){
  const f = readForm();
  if(!f.name){ toast("模型名稱不能為空", true); return; }
  if(!f.cat){ toast("請選擇分類", true); return; }
  if(!f.root){ toast("請選擇所屬根", true); return; }
  const btn = $("#saveBtn");
  btn.disabled = true; btn.textContent = "保存中…";
  const path = "models/" + String(f.n).padStart(3,"0") + ".md";
  const ok = await ghPutFile(path, formToMd(f), `✎ ${f.name} (No.${f.n})`);
  btn.disabled = false; btn.textContent = "保存到 GitHub ↗";
  if(!ok) return;
  const model = {
    n: f.n, name: f.name, cat: f.cat, root: f.root, bv: f.bv, vw: f.vw,
    core: f.core, pts: f.pts, sc: f.sc,
    talk: f.talk, case: f.case, quote: f.quote, src: f.src, extra: f.extra,
    is_core: f.is_core
  };
  const i = DATA.models.findIndex(x => x.n === f.n);
  if(i >= 0) DATA.models[i] = model; else DATA.models.push(model);
  DATA.models.sort((a,b)=>a.n-b.n);
  renderGrid();
  toast("已保存到 GitHub ✓（data.json 自動重建，下次載入生效）");
  closeEditor();
}
function openSettings(){
  const s = ghSettings() || {};
  $("#s_owner").value = s.owner || REPO_DEFAULT.owner;
  $("#s_repo").value = s.repo || REPO_DEFAULT.repo;
  $("#s_branch").value = s.branch || REPO_DEFAULT.branch;
  $("#s_token").value = s.token || "";
  $("#settingsModal").classList.add("open");
}
function closeSettings(){ $("#settingsModal").classList.remove("open"); }
async function saveSettings(){
  const s = {
    owner: $("#s_owner").value.trim(),
    repo: $("#s_repo").value.trim(),
    branch: $("#s_branch").value.trim() || "main",
    token: $("#s_token").value.trim()
  };
  if(!s.owner || !s.repo){ toast("Owner 與 Repo 必填", true); return; }
  saveGhSettings(s);
  closeSettings();
  toast("設定已保存，正在拉取最新數據…");
  const ok = await fetchLive();
  toast(ok ? "已連接，數據已更新 ✓" : "已保存（暫無法拉取，將使用內置數據）", !ok);
}

/* 初始化 */
renderCats();
renderGrid();
fetchLive();
</script>
</body>
</html>
"""


def build(do_md=False):
    models = load_models()
    total_views = sum(m["vw"] for m in models)
    data_json = json.dumps({"models": models, "roots": ROOTS}, ensure_ascii=False)

    html = TEMPLATE
    html = html.replace("__DATA__", data_json)
    html = html.replace("__CAT_ICONS__", json.dumps(CAT_ICONS, ensure_ascii=False))
    html = html.replace("__CAT_ORDER__", json.dumps(CAT_ORDER, ensure_ascii=False))
    html = html.replace("__VIEWS__", f"{(total_views/10000):.0f}萬")
    html = html.replace("__REPO_DEFAULT__", json.dumps(REPO_DEFAULT, ensure_ascii=False))

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    os.makedirs(SITE_DIR, exist_ok=True)
    with open(SITE_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        f.write(data_json)

    print(f"build ok: {len(models)} models, {len(html)} chars -> 思维模型手册.html + site/index.html + data.json")
    if do_md:
        gen_md(models)
    return models


def gen_md(models):
    L = ["# 100個思維模型 · 檀東東Tango", ""]
    L.append(f"> 合集 78 支視頻 · 基於語音轉寫稿提煉\n")
    for r in ROOTS:
        L.append(f"## 根：{r['name']}（{r['en']}）— {r['desc']}")
        L.append("")
        for m in [x for x in models if x["root"] == r["id"]]:
            tag = " ★核心" if m["is_core"] else ""
            L.append(f"### No.{m['n']:03d} {m['name']}{tag}")
            L.append(f"- 分類：{m['cat']} · 播放 {m['vw']}")
            L.append(f"- 核心：{m['core']}")
            L.append(f"- 要點：{'；'.join(m['pts'])}")
            L.append(f"- 場景：{'、'.join(m['sc'])}")
            if m["talk"]:
                L.append(f"- 博主講解：{m['talk']}")
            if m["case"]:
                L.append(f"- 案例：{m['case']}")
            if m["quote"]:
                L.append(f"- 名言：{m['quote']}")
            L.append(f"- 原視頻：https://www.bilibili.com/video/{m['bv']}")
            L.append("")
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"md ok -> 思维模型手册.md")


def watch(do_md=False):
    watch_paths = [MODELS_DIR, os.path.abspath(__file__)]
    def mtime():
        return max(os.path.getmtime(p) for p in watch_paths if os.path.exists(p))
    last = mtime()
    print(f"[watch] 监听 {MODELS_DIR} 与 build.py，改动即重建（Ctrl+C 退出）")
    build(do_md)
    while True:
        time.sleep(1)
        try:
            now = mtime()
        except FileNotFoundError:
            continue
        if now != last:
            last = now
            try:
                build(do_md)
            except Exception as e:
                print("[watch] build 失败:", e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true", help="监听改动自动重建")
    ap.add_argument("--md", action="store_true", help="额外导出 Markdown")
    args = ap.parse_args()
    if args.watch:
        watch(args.md)
    else:
        build(args.md)
