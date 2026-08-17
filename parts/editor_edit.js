/* ============================================================
   網頁內編輯層：直接在頁面修改內容 → 存本地草稿 → 推送回 GitHub
   資料來源為 data.js 的 CATS / MODELS（同一 global scope，直接原地改寫）
   ============================================================ */
const MM = {
  editMode: false,
  curNo: null,
  LS: { draft:'mm_draft_v1', pushed:'mm_pushed_v1', cfg:'mm_gh_cfg_v1', token:'mm_gh_token_v1' },
  FIELDS: ['no','name','cat','tag','bv','thought','points','scenes','explain','extend','tips','related'],
  HEADER: '// 思维模型数据 · 来源：B站「檀東東Tango」《100個思維模型》合集转写整理\n'
        + '// 修改内容只需编辑此文件并刷新页面，无需改动 handbook。\n'
};
window.MM = MM;

/* ---------- 資料存取（供 console 調試 / 外部程式使用） ---------- */
MM.models = () => MODELS;
MM.cats = () => CATS;
MM.get = no => noMap[no];

/* ---------- 快照 / 序列化 ---------- */
MM.snapshot = () => JSON.stringify({ CATS, MODELS });
MM.serialize = () => MM.HEADER
  + '// 最後更新：' + new Date().toLocaleString('zh-Hant') + '（由網頁編輯器寫入）\n'
  + 'const CATS = ' + JSON.stringify(CATS, null, 2) + ';\n\n'
  + 'const MODELS = ' + JSON.stringify(MODELS, null, 2) + ';\n';

MM.fileSnap = MM.snapshot();               // data.js 載入時的內容
MM.lsGet = k => { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch(e){ return null; } };
MM.lsSet = (k,v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} };

/* ---------- 資料整體替換（草稿載入 / 遠端拉取） ---------- */
MM.applyData = (cats, models) => {
  Object.keys(CATS).forEach(k => { delete CATS[k]; });
  Object.keys(cats).forEach(k => { CATS[k] = cats[k]; });
  MODELS.length = 0;
  models.forEach(m => MODELS.push(m));
  MM.reindex(); MM.rebuildTabs(); MM.refreshMeta(); render();
};

MM.reindex = () => {
  Object.keys(byName).forEach(k => { delete byName[k]; });
  Object.keys(noMap).forEach(k => { delete noMap[k]; });
  MODELS.forEach(m => { byName[m.name] = m; noMap[m.no] = m; });
};
MM.rebuildTabs = () => {
  const names = ['全部', ...Object.keys(CATS)];
  if (!names.includes(curCat)) curCat = '全部';
  tabsEl.innerHTML = names.map(c => {
    const n = c === '全部' ? MODELS.length : MODELS.filter(m => m.cat === c).length;
    return `<div class="tab${c === curCat ? ' on' : ''}" data-cat="${c}">${c}<small>${n}</small></div>`;
  }).join('');
};
MM.refreshMeta = () => {
  document.getElementById('metaCount').textContent = '共收錄 ' + MODELS.length + ' 個模型';
  document.getElementById('navMeta').textContent = MODELS.length + ' 個模型 · 五根分類';
};

/* ---------- 草稿 / 未推送狀態 ---------- */
MM.persistDraft = () => {
  const snap = MM.snapshot();
  if (snap === MM.fileSnap) localStorage.removeItem(MM.LS.draft);
  else MM.lsSet(MM.LS.draft, { snap, at: Date.now() });
  MM.updateDirty();
};
MM.isDirty = () => {
  const pushed = MM.lsGet(MM.LS.pushed);
  return MM.snapshot() !== (pushed && pushed.snap ? pushed.snap : MM.fileSnap);
};
MM.updateDirty = () => {
  const d = MM.isDirty();
  const b = document.getElementById('syncBtn');
  b.classList.toggle('dirty', d);
  b.title = d ? '有未推送到 GitHub 的修改' : '內容與最近一次同步一致';
};

/* ---------- toast ---------- */
MM.toast = (msg, err) => {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  clearTimeout(MM._tt);
  MM._tt = setTimeout(() => { t.className = 'toast'; }, err ? 4200 : 2400);
};

/* ---------- 編輯模式開關 ---------- */
MM.setEditMode = on => {
  MM.editMode = on;
  document.body.classList.toggle('editmode', on);
  document.getElementById('editToggle').classList.toggle('on', on);
  document.getElementById('editHint').className = 'edit-hint' + (on ? ' show' : '');
  document.getElementById('editThis').style.display = (on && MM.curNo) ? '' : 'none';
  MM.lsSet('mm_editmode', on);
};

/* ---------- 詳情頁：讀取模式包一層，記住當前模型 ---------- */
const _openDetail = window.openDetail;
window.openDetail = function(no){
  MM.curNo = no;
  _openDetail(no);
  document.getElementById('editThis').style.display = MM.editMode ? '' : 'none';
};
const _closeDetail = window.closeDetail;
window.closeDetail = function(){
  MM.curNo = null;
  document.getElementById('editThis').style.display = 'none';
  _closeDetail();
};

/* ---------- 編輯表單 ---------- */
const lines = v => (Array.isArray(v) ? v : []).join('\n');
const toList = s => s.split('\n').map(x => x.trim()).filter(Boolean);
const nextNo = () => {
  const max = MODELS.reduce((a,m) => Math.max(a, parseInt(m.no,10) || 0), 0);
  return String(max + 1).padStart(3,'0');
};

MM.startEdit = function(no){
  const isNew = no === '__new__';
  const m = isNew
    ? { no: nextNo(), name:'', cat:Object.keys(CATS)[0], tag:'', bv:'', thought:'',
        points:[], scenes:[], explain:'', extend:'', tips:'', related:[] }
    : noMap[no];
  if (!m) return;
  const color = cc(m.cat);
  const catOpts = Object.keys(CATS).map(c =>
    `<option value="${esc(c)}"${c === m.cat ? ' selected' : ''}>${esc(c)}</option>`).join('');

  detailBody.innerHTML = `
    <div class="ed-head" style="--cc:${color}">
      <h2>${isNew ? '新增模型' : '編輯：' + esc(m.name)}</h2>
      <span class="who">${isNew ? '將加入為 No.' + esc(m.no) : 'No.' + esc(m.no)}</span>
    </div>
    <p class="ed-note">直接改下面欄位 → 按「儲存」立即生效並存成本地草稿；要寫回 GitHub 請按右上「⇅ 同步」。<br>清單類欄位（關鍵要點 / 適用場景 / 同根模型）<b>一行一項</b>。</p>

    <div class="frow">
      <div class="f${isNew ? '' : ' ro'}"><label>編號 No.</label>
        <input type="text" id="ed_no" value="${esc(m.no)}"${isNew ? '' : ' readonly'}></div>
      <div class="f"><label>分類（五根）</label><select id="ed_cat">${catOpts}</select></div>
    </div>
    <div class="f"><label>模型名稱</label><input type="text" id="ed_name" value="${esc(m.name)}"></div>
    <div class="f"><label>一句話簡介（卡片上顯示）</label><textarea id="ed_tag" rows="2">${esc(m.tag)}</textarea></div>
    <div class="f"><label>核心思想</label><textarea id="ed_thought" rows="3">${esc(m.thought)}</textarea></div>
    <div class="f"><label>關鍵要點（一行一項）</label><textarea id="ed_points" rows="6">${esc(lines(m.points))}</textarea></div>
    <div class="f"><label>適用場景（一行一項）</label><textarea id="ed_scenes" rows="5">${esc(lines(m.scenes))}</textarea></div>
    <div class="f"><label>博主講解</label><textarea id="ed_explain" rows="6">${esc(m.explain)}</textarea></div>
    <div class="f"><label>延伸學習</label><textarea id="ed_extend" rows="4">${esc(m.extend)}</textarea></div>
    <div class="f"><label>實用提醒</label><textarea id="ed_tips" rows="4">${esc(m.tips)}</textarea></div>
    <div class="f"><label>同根模型（一行一個名稱）</label><textarea id="ed_related" rows="4">${esc(lines(m.related))}</textarea>
      <div class="tipline">名稱與現有模型一致時會自動變成可點擊的跳轉標籤。</div></div>
    <div class="f"><label>Bilibili BV 號</label><input type="text" id="ed_bv" value="${esc(m.bv)}">
      <div class="tipline">例：BV1xx411c7XX，會組成頁尾原視頻連結。</div></div>

    <div class="ed-actions">
      <button class="btn" onclick="MM.saveEdit(${isNew ? 'true' : 'false'})">儲存</button>
      <button class="btn ghost" onclick="MM.cancelEdit('${isNew ? '' : esc(m.no)}')">取消</button>
      ${isNew ? '' : `<button class="btn danger" onclick="MM.delModel('${esc(m.no)}')">刪除此模型</button>`}
    </div>`;
  crumb.textContent = (isNew ? '新增' : '編輯') + ' · ' + (isNew ? '未儲存' : 'No.' + m.no);
  detail.classList.add('open');
  document.body.style.overflow = 'hidden';
  detail.scrollTop = 0;
  document.getElementById('editThis').style.display = 'none';
  MM._editingNew = isNew;
  MM._editingNo = m.no;
};

MM.saveEdit = function(isNew){
  const val = id => document.getElementById('ed_' + id).value;
  const no = val('no').trim(), name = val('name').trim();
  if (!no)   return MM.toast('編號不能空白', true);
  if (!name) return MM.toast('模型名稱不能空白', true);
  if (isNew && noMap[no]) return MM.toast('編號 ' + no + ' 已存在，換一個', true);

  const obj = {
    no, name, cat: val('cat'), tag: val('tag').trim(), bv: val('bv').trim(),
    thought: val('thought').trim(), points: toList(val('points')), scenes: toList(val('scenes')),
    explain: val('explain').trim(), extend: val('extend').trim(), tips: val('tips').trim(),
    related: toList(val('related'))
  };
  if (isNew) MODELS.push(obj);
  else {
    const t = noMap[MM._editingNo];
    const oldName = t.name;
    MM.FIELDS.forEach(f => { t[f] = obj[f]; });
    if (oldName !== obj.name) delete byName[oldName];
  }
  MODELS.sort((a,b) => String(a.no).localeCompare(String(b.no)));
  MM.reindex(); MM.rebuildTabs(); MM.refreshMeta(); render(); MM.persistDraft();
  MM.toast('已儲存「' + name + '」（本地草稿，尚未推送）');
  window.openDetail(no);
};

MM.cancelEdit = function(no){
  if (no && noMap[no]) window.openDetail(no);
  else window.closeDetail();
};

MM.delModel = function(no){
  const m = noMap[no]; if (!m) return;
  if (!confirm('確定刪除 No.' + no + '「' + m.name + '」？\n刪除後仍可按「棄用本地草稿」還原到上次同步的版本。')) return;
  MODELS.splice(MODELS.findIndex(x => x.no === no), 1);
  MM.reindex(); MM.rebuildTabs(); MM.refreshMeta(); render(); MM.persistDraft();
  window.closeDetail();
  MM.toast('已刪除 No.' + no + '（本地草稿）');
};
