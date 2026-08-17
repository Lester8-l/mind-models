# 100 個思維模型 · 檀東東Tango

B站合集《100個思維模型》（UP主：檀東東Tango，共 78 支視頻）整理為可迭代的思維模型庫。

## 結構

| 路徑 | 作用 |
|---|---|
| `models/NNN.md` | **单一事实源**：每个模型一个 Markdown（frontmatter 元数据 + 正文讲解），直接编辑即更新 |
| `build.py` | 生成器：`models/*.md` → `site/index.html`（网页）/ `data.json`（网页实时拉取）/ 手册 MD |
| `data.json` | 编译产物，网页从 GitHub 实时拉取；push 后由 GitHub Action 自动重建 |
| `.github/workflows/rebuild.yml` | push 到 `models/` 或 `build.py` 时自动重新编译 `data.json` |

## 日常用法

- **改文案 / 加模型**：直接编辑或新建 `models/NNN.md`，推送到仓库即可（Action 自动重建 data.json）
- **在网页里编辑**：打开站点 → ⚙ 設定填入 Owner/Repo/Branch/Token → 卡片 ✎ 或「＋ 新增模型」→ 保存即写回 GitHub
- **本地构建**：`python build.py`（或 `--watch` 监听自动重建、`--md` 额外导出手册）

## 前端架构

单文件 HTML（Sprig 暖纸编辑风），五根结构（想清楚/做到位/说得好/带得动/走得远），78 模型，20 核心标记。数据内嵌作兜底，有设置时启动自动 `fetchLive()` 从 `raw.githubusercontent.com/…/data.json` 拉最新。

Token 仅存于浏览器 localStorage，用于 GitHub Contents API 写入，不入库。
