/* ============================================================
   GitHub 同步層：把 data.js 拉下來 / 推回去（Contents API）
   Token 只存本機 localStorage，不會寫進任何檔案
   ============================================================ */
MM.CFG_DEFAULT = { owner:'Lester8-l', repo:'mind-models', branch:'main', path:'data.js',
                   msg:'chore: 更新 data.js（網頁編輯器）', auto:false };
MM.cfg = Object.assign({}, MM.CFG_DEFAULT, MM.lsGet(MM.LS.cfg) || {});
MM.token = () => localStorage.getItem(MM.LS.token) || '';

/* ---------- UI 注入 ---------- */
document.querySelector('nav .wrap').insertAdjacentHTML('beforeend', `
  <div class="nav-actions">
    <button class="mini-btn" id="editToggle" title="開啟後可直接在頁面修改內容">✎ 編輯模式</button>
    <button class="mini-btn" id="syncBtn" title="與 GitHub 同步">⇅ 同步<span class="dot-dirty"></span></button>
  </div>`);

document.getElementById('home').insertAdjacentHTML('afterbegin', `
  <div class="edit-hint" id="editHint">
    <span class="grow">編輯模式已開啟：點任一卡片進入詳情，按左上「✎ 編輯」修改內容；改完在「⇅ 同步」推回 GitHub。</span>
    <button class="new-btn" onclick="MM.startEdit('__new__')">＋ 新增模型</button>
  </div>`);

document.querySelector('.detail-bar .wrap').insertAdjacentHTML('beforeend', `
  <button class="back-btn" id="editThis" style="display:none;margin-left:auto"
          onclick="MM.startEdit(MM.curNo)">✎ 編輯此篇</button>`);

document.body.insertAdjacentHTML('beforeend', `
  <div class="modal" id="syncModal">
    <div class="modal-card">
      <div class="modal-head">
        <h3>同步到 GitHub</h3>
        <button class="x-btn" onclick="MM.closeSync()">✕</button>
      </div>
      <div class="modal-body">
        <div class="sync-state" id="syncState"></div>
        <div class="f"><label>GitHub Token（需 repo 寫入權限）</label>
          <input type="password" id="cfgToken" placeholder="ghp_… 或 github_pat_…" autocomplete="off"></div>
        <div class="frow">
          <div class="f"><label>Owner</label><input type="text" id="cfgOwner"></div>
          <div class="f"><label>Repo</label><input type="text" id="cfgRepo"></div>
        </div>
        <div class="frow">
          <div class="f"><label>Branch</label><input type="text" id="cfgBranch"></div>
          <div class="f"><label>檔案路徑</label><input type="text" id="cfgPath"></div>
        </div>
        <div class="f"><label>Commit 訊息</label><input type="text" id="cfgMsg"></div>
        <label class="chk"><input type="checkbox" id="cfgAuto">
          <span>每次開啟頁面時，自動從 GitHub 拉取最新內容（沒有未推送修改時才會拉）</span></label>
        <div class="modal-actions">
          <button class="btn" onclick="MM.push()">推送到 GitHub</button>
          <button class="btn ghost" onclick="MM.pull(false)">拉取遠端最新</button>
          <button class="btn ghost" onclick="MM.download()">下載 data.js</button>
          <button class="btn danger" onclick="MM.discard()">棄用本地草稿</button>
        </div>
        <pre class="log" id="syncLog"></pre>
        <p class="hint">Token 只保存在這台電腦的瀏覽器（localStorage），不會寫入 data.js、也不會隨頁面上傳。建議用 Fine-grained token 並只授權這個 repo 的 Contents 讀寫。</p>
      </div>
    </div>
  </div>
  <div class="toast" id="toast"></div>`);

/* ---------- 小工具 ---------- */
const b64enc = s => { const by = new TextEncoder().encode(s); let bin=''; by.forEach(b => bin += String.fromCharCode(b)); return btoa(bin); };
const b64dec = s => new TextDecoder().decode(Uint8Array.from(atob(String(s).replace(/\s/g,'')), c => c.charCodeAt(0)));
MM.log = (m, clear) => {
  const el = document.getElementById('syncLog');
  el.classList.add('show');
  el.textContent = (clear ? '' : el.textContent + (el.textContent ? '\n' : '')) + m;
  el.scrollTop = el.scrollHeight;
};
MM.apiUrl = () => `https://api.github.com/repos/${MM.cfg.owner}/${MM.cfg.repo}/contents/`
  + MM.cfg.path.split('/').map(encodeURIComponent).join('/');
MM.headers = () => {
  const h = { 'Accept':'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28' };
  const t = MM.token(); if (t) h.Authorization = 'Bearer ' + t;
  return h;
};
MM.parseDataJs = txt => {
  const o = new Function(txt + '\nreturn { CATS: typeof CATS!=="undefined"?CATS:null, MODELS: typeof MODELS!=="undefined"?MODELS:null };')();
  if (!o.CATS || !Array.isArray(o.MODELS) || !o.MODELS.length) throw new Error('data.js 內容不含有效的 CATS / MODELS');
  return o;
};

/* ---------- 設定面板 ---------- */
MM.openSync = () => {
  const c = MM.cfg;
  document.getElementById('cfgToken').value  = MM.token();
  document.getElementById('cfgOwner').value  = c.owner;
  document.getElementById('cfgRepo').value   = c.repo;
  document.getElementById('cfgBranch').value = c.branch;
  document.getElementById('cfgPath').value   = c.path;
  document.getElementById('cfgMsg').value    = c.msg;
  document.getElementById('cfgAuto').checked = !!c.auto;
  const pushed = MM.lsGet(MM.LS.pushed);
  const dirty = MM.isDirty();
  document.getElementById('syncState').innerHTML =
    `本地共 <b>${MODELS.length}</b> 個模型 · 狀態：` +
    (dirty ? '<span class="warn">有未推送的修改</span>' : '<b>已與最近一次同步一致</b>') +
    (pushed && pushed.at ? `<br>最近同步：${new Date(pushed.at).toLocaleString('zh-Hant')}` : '<br>尚未做過同步');
  document.getElementById('syncLog').className = 'log';
  document.getElementById('syncModal').classList.add('open');
};
MM.closeSync = () => {
  MM.cfg = { owner:v('cfgOwner')||MM.CFG_DEFAULT.owner, repo:v('cfgRepo')||MM.CFG_DEFAULT.repo,
             branch:v('cfgBranch')||'main', path:v('cfgPath')||'data.js',
             msg:v('cfgMsg')||MM.CFG_DEFAULT.msg, auto:document.getElementById('cfgAuto').checked };
  MM.lsSet(MM.LS.cfg, MM.cfg);
  const t = v('cfgToken');
  if (t) localStorage.setItem(MM.LS.token, t); else localStorage.removeItem(MM.LS.token);
  document.getElementById('syncModal').classList.remove('open');
};
function v(id){ return document.getElementById(id).value.trim(); }
MM.saveCfgInline = () => {
  MM.cfg = Object.assign(MM.cfg, { owner:v('cfgOwner'), repo:v('cfgRepo'), branch:v('cfgBranch')||'main',
                                   path:v('cfgPath')||'data.js', msg:v('cfgMsg')||MM.CFG_DEFAULT.msg,
                                   auto:document.getElementById('cfgAuto').checked });
  MM.lsSet(MM.LS.cfg, MM.cfg);
  const t = v('cfgToken');
  if (t) localStorage.setItem(MM.LS.token, t); else localStorage.removeItem(MM.LS.token);
};

/* ---------- 推送 ---------- */
MM.push = async () => {
  MM.saveCfgInline();
  if (!MM.token()) return MM.log('✗ 請先填 GitHub Token（需要 repo Contents 寫入權限）', true);
  const text = MM.serialize();
  try { MM.parseDataJs(text); } catch(e){ return MM.log('✗ 產生的 data.js 無法解析，已中止：' + e.message, true); }
  MM.log('① 讀取遠端 ' + MM.cfg.path + ' 的 sha …', true);
  try{
    let sha = null;
    const g = await fetch(MM.apiUrl() + '?ref=' + encodeURIComponent(MM.cfg.branch), { headers: MM.headers() });
    if (g.status === 200) { sha = (await g.json()).sha; MM.log('   已存在，sha=' + sha.slice(0,10) + '…'); }
    else if (g.status === 404) MM.log('   遠端還沒有這個檔案，將新建');
    else throw new Error('讀取失敗 HTTP ' + g.status + ' ' + ((await g.json().catch(()=>({}))).message || ''));

    MM.log('② 上傳中（' + (text.length/1024).toFixed(1) + ' KB）…');
    const p = await fetch(MM.apiUrl(), {
      method:'PUT', headers: Object.assign({'Content-Type':'application/json'}, MM.headers()),
      body: JSON.stringify({ message: MM.cfg.msg, content: b64enc(text), branch: MM.cfg.branch, sha: sha || undefined })
    });
    const pj = await p.json().catch(()=>({}));
    if (!p.ok) throw new Error('HTTP ' + p.status + ' ' + (pj.message || ''));
    MM.lsSet(MM.LS.pushed, { snap: MM.snapshot(), at: Date.now() });
    MM.updateDirty();
    const c = pj.commit || {};
    MM.log('✓ 推送成功　commit ' + String(c.sha||'').slice(0,7) + '\n   ' + (c.html_url || ''));
    MM.toast('已推送到 GitHub：' + MM.cfg.owner + '/' + MM.cfg.repo);
  }catch(e){
    MM.log('✗ 推送失敗：' + e.message + '\n（常見原因：token 沒有該 repo 的 Contents 寫入權限、branch 名稱不對、路徑不存在）');
    MM.toast('推送失敗：' + e.message, true);
  }
};

/* ---------- 拉取 ---------- */
MM.pull = async silent => {
  MM.saveCfgInline();
  if (!silent && MM.isDirty() && !confirm('本地有未推送的修改，拉取會用遠端內容覆蓋。要繼續嗎？')) return;
  const raw = `https://raw.githubusercontent.com/${MM.cfg.owner}/${MM.cfg.repo}/${MM.cfg.branch}/${MM.cfg.path}?t=` + Date.now();
  if (!silent) MM.log('① 讀取遠端內容 …', true);
  try{
    let text;
    if (MM.token()){
      const r = await fetch(MM.apiUrl() + '?ref=' + encodeURIComponent(MM.cfg.branch), { headers: MM.headers() });
      if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + ((await r.json().catch(()=>({}))).message || ''));
      text = b64dec((await r.json()).content);
    } else {
      /* 無 token：先試 raw，被限流（429）或失敗時改走 Contents API 匿名讀取 */
      let r = await fetch(raw, { cache:'no-store' }).catch(() => null);
      if (r && r.ok) text = await r.text();
      else {
        if (!silent) MM.log('   raw 取檔失敗' + (r ? '（HTTP ' + r.status + '）' : '') + '，改用 GitHub API …');
        const r2 = await fetch(MM.apiUrl() + '?ref=' + encodeURIComponent(MM.cfg.branch), { headers: MM.headers() });
        if (!r2.ok) throw new Error('HTTP ' + r2.status + ' ' + ((await r2.json().catch(()=>({}))).message || '（私有 repo 請填 token）'));
        text = b64dec((await r2.json()).content);
      }
    }
    const o = MM.parseDataJs(text);
    MM.applyData(o.CATS, o.MODELS);
    MM.fileSnap = MM.snapshot();
    localStorage.removeItem(MM.LS.draft);
    MM.lsSet(MM.LS.pushed, { snap: MM.snapshot(), at: Date.now() });
    MM.updateDirty();
    if (!silent){ MM.log('✓ 已載入遠端內容：' + o.MODELS.length + ' 個模型'); MM.toast('已拉取遠端最新內容（' + o.MODELS.length + ' 個模型）'); }
    else console.log('[MM] 自動拉取成功：' + o.MODELS.length + ' 個模型');
  }catch(e){
    if (!silent){ MM.log('✗ 拉取失敗：' + e.message); MM.toast('拉取失敗：' + e.message, true); }
    else console.warn('[MM] 自動拉取失敗：' + e.message);
  }
};

/* ---------- 下載 / 棄用草稿 ---------- */
MM.download = () => {
  const blob = new Blob([MM.serialize()], { type:'text/javascript;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'data.js';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
  MM.toast('已下載 data.js，覆蓋原檔即可離線生效');
};
MM.discard = () => {
  if (!localStorage.getItem(MM.LS.draft)) return MM.toast('目前沒有本地草稿');
  if (!confirm('棄用本地草稿，回到 data.js 原本的內容？此動作無法復原。')) return;
  localStorage.removeItem(MM.LS.draft);
  localStorage.removeItem(MM.LS.pushed);
  location.reload();
};

/* ---------- 事件綁定 ---------- */
document.getElementById('editToggle').addEventListener('click', () => MM.setEditMode(!MM.editMode));
document.getElementById('syncBtn').addEventListener('click', MM.openSync);
document.getElementById('syncModal').addEventListener('click', e => { if (e.target.id === 'syncModal') MM.closeSync(); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.getElementById('syncModal').classList.contains('open')){
    e.stopImmediatePropagation(); MM.closeSync();
  }
}, true);

/* ---------- 啟動：載入草稿 / 還原編輯模式 / 自動拉取 ---------- */
(function init(){
  const draft = MM.lsGet(MM.LS.draft);
  if (draft && draft.snap && draft.snap !== MM.fileSnap){
    try{
      const d = JSON.parse(draft.snap);
      MM.applyData(d.CATS, d.MODELS);
      MM.toast('已載入本地草稿（' + new Date(draft.at).toLocaleString('zh-Hant') + '）');
    }catch(e){ console.warn('草稿載入失敗', e); }
  }
  MM.setEditMode(!!MM.lsGet('mm_editmode'));
  MM.updateDirty();
  if (MM.cfg.auto && !MM.isDirty()) MM.pull(true);
})();
