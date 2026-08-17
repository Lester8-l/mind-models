/* 用 jsdom 真實跑一遍：編輯模式 → 改內容 → 存草稿 → 推送/拉取 GitHub（fetch 以假 API 模擬） */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require(path.join('C:/Users/Jason/.workbuddy/binaries/node/workspace', 'node_modules/jsdom'));

const DIR = 'C:/Users/Jason/WorkBuddy/2026-08-17-12-59-09';
const dataJs = fs.readFileSync(path.join(DIR, 'data.js'), 'utf8');
const htmlRaw = fs.readFileSync(path.join(DIR, '思维模型手册.html'), 'utf8');
// 把外部 data.js 內聯，避免 jsdom 載入外部資源
const html = htmlRaw.replace('<script src="data.js"></script>', '<script>' + dataJs + '</script>');

const calls = [];
function makeDom(seedDraft, remoteText) {
  return new JSDOM(html, {
    url: 'https://local.test/handbook.html',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(w) {
      w.confirm = () => true;
      w.URL.createObjectURL = () => 'blob:x';
      w.URL.revokeObjectURL = () => {};
      w.HTMLAnchorElement.prototype.click = function () {};
      if (seedDraft) w.localStorage.setItem('mm_draft_v1', JSON.stringify({ snap: seedDraft, at: Date.now() }));
      w.fetch = async (url, opt) => {
        opt = opt || {};
        calls.push({ url: String(url), method: opt.method || 'GET', body: opt.body, auth: !!(opt.headers && opt.headers.Authorization) });
        if (String(url).includes('raw.githubusercontent.com'))
          return { ok: true, status: 200, text: async () => remoteText };
        if (opt.method === 'PUT')
          return { ok: true, status: 200, json: async () => ({ commit: { sha: 'deadbeef1234', html_url: 'https://github.com/x/y/commit/deadbeef' } }) };
        return { ok: true, status: 200, json: async () => ({ sha: 'oldsha0001', content: Buffer.from(remoteText || dataJs, 'utf8').toString('base64') }) };
      };
    }
  });
}

const ok = (label, cond, extra) => console.log((cond ? '  ✓ ' : '  ✗ ') + label + (extra !== undefined ? '  → ' + extra : ''));

(async () => {
  /* ========== A. 基本渲染 + 編輯層掛載 ========== */
  console.log('A. 渲染與編輯層');
  const dom = makeDom();
  const w = dom.window, d = w.document;
  const MM = w.MM;
  ok('MM 已掛載', !!MM);
  ok('卡片渲染', d.querySelectorAll('#grid .card').length === 77, d.querySelectorAll('#grid .card').length + ' 張');
  ok('nav 有編輯/同步按鈕', !!d.getElementById('editToggle') && !!d.getElementById('syncBtn'));
  ok('初始未有未推送修改', !MM.isDirty());

  /* ========== B. 編輯模式 ========== */
  console.log('B. 編輯模式');
  d.getElementById('editToggle').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  ok('body 加上 editmode', d.body.classList.contains('editmode'));
  ok('提示條顯示', d.getElementById('editHint').className.includes('show'));
  w.openDetail('008');
  ok('詳情頁開啟', d.getElementById('detail').classList.contains('open'));
  ok('「編輯此篇」按鈕出現', d.getElementById('editThis').style.display !== 'none');

  /* ========== C. 改內容並儲存 ========== */
  console.log('C. 修改並儲存');
  MM.startEdit('008');
  ok('表單欄位齊全', ['no','name','cat','tag','thought','points','scenes','explain','extend','tips','related','bv']
      .every(f => d.getElementById('ed_' + f)));
  ok('原值帶入', d.getElementById('ed_name').value === 'ABC（信念）', d.getElementById('ed_name').value);
  d.getElementById('ed_name').value = 'ABC（信念）· 測試改名';
  d.getElementById('ed_points').value = '要點一\n要點二\n要點三';
  d.getElementById('ed_tips').value = '測試提醒';
  MM.saveEdit(false);
  const m8 = w.MM.models().find(m => m.no === '008');
  ok('名稱已更新', m8.name === 'ABC（信念）· 測試改名', m8.name);
  ok('清單欄位轉陣列', Array.isArray(m8.points) && m8.points.length === 3, JSON.stringify(m8.points));
  ok('狀態變為未推送', MM.isDirty());
  ok('草稿已寫 localStorage', !!w.localStorage.getItem('mm_draft_v1'));
  ok('列表重繪後名稱同步', d.getElementById('grid').innerHTML.includes('測試改名'));
  ok('存檔後回到閱讀模式', d.getElementById('detailBody').innerHTML.includes('關鍵要點'));

  /* ========== D. 新增 / 刪除 ========== */
  console.log('D. 新增與刪除');
  MM.startEdit('__new__');
  ok('新增自動配編號 078', d.getElementById('ed_no').value === '078', d.getElementById('ed_no').value);
  d.getElementById('ed_name').value = '測試新模型';
  d.getElementById('ed_tag').value = '一句話簡介';
  d.getElementById('ed_cat').value = '做到位';
  MM.saveEdit(true);
  ok('模型數 78', w.MM.models().length === 78, w.MM.models().length);
  ok('分類頁籤計數更新', d.getElementById('tabs').innerHTML.includes('做到位<small>9</small>'));
  const serialized = MM.serialize();
  const parsed = new Function(serialized + '\nreturn {CATS, MODELS};')();
  ok('序列化可反解析', parsed.MODELS.length === 78);
  ok('序列化含新模型', parsed.MODELS.some(m => m.name === '測試新模型'));
  MM.delModel('078');
  ok('刪除後回到 77', w.MM.models().length === 77, w.MM.models().length);

  /* ========== E. 推送到 GitHub ========== */
  console.log('E. 推送 GitHub');
  MM.openSync();
  ok('同步面板開啟', d.getElementById('syncModal').classList.contains('open'));
  ok('狀態顯示未推送', d.getElementById('syncState').innerHTML.includes('未推送'));
  d.getElementById('cfgToken').value = 'ghp_test_token';
  await MM.push();
  const put = calls.find(c => c.method === 'PUT');
  ok('先 GET 取 sha', calls.some(c => c.method === 'GET' && c.url.includes('/contents/data.js')));
  ok('再 PUT 上傳', !!put);
  ok('PUT 帶 Authorization', put && put.auth);
  const body = JSON.parse(put.body);
  ok('PUT 帶 sha 與 branch', body.sha === 'oldsha0001' && body.branch === 'main', body.branch);
  const uploaded = Buffer.from(body.content, 'base64').toString('utf8');
  ok('上傳內容含改名結果', uploaded.includes('測試改名'));
  ok('上傳內容可解析', new Function(uploaded + '\nreturn MODELS;')().length === 77);
  ok('推送後標記為已同步', !MM.isDirty());
  ok('log 顯示成功', d.getElementById('syncLog').textContent.includes('推送成功'));

  /* ========== F. 拉取遠端 ========== */
  console.log('F. 拉取遠端');
  const remote = dataJs.replace('"name": "ABC（信念）"', '"name": "遠端版本名稱"');
  const dom2 = makeDom(null, remote);
  const w2 = dom2.window, d2 = w2.document;
  d2.getElementById('cfgToken') || w2.MM.openSync();
  w2.MM.openSync();
  d2.getElementById('cfgToken').value = '';   // 公開 repo：走 raw
  await w2.MM.pull(false);
  ok('走 raw 取檔', calls.some(c => c.url.includes('raw.githubusercontent.com')));
  ok('已套用遠端內容', w2.MM.models().some(m => m.name === '遠端版本名稱'));
  ok('拉取後清空草稿', !w2.localStorage.getItem('mm_draft_v1'));
  ok('拉取後為已同步', !w2.MM.isDirty());

  /* ========== G. 草稿在重新載入後還原 ========== */
  console.log('G. 草稿還原');
  const draftSnap = JSON.stringify({
    CATS: new Function(dataJs + '\nreturn CATS;')(),
    MODELS: new Function(dataJs + '\nreturn MODELS;')().map(m => m.no === '008' ? Object.assign({}, m, { name: '草稿還原測試' }) : m)
  });
  const dom3 = makeDom(draftSnap);
  const w3 = dom3.window;
  ok('重新載入自動套用草稿', w3.MM.models().find(m => m.no === '008').name === '草稿還原測試');
  ok('草稿狀態=未推送', w3.MM.isDirty());
  ok('卡片也用草稿內容', dom3.window.document.getElementById('grid').innerHTML.includes('草稿還原測試'));

  console.log('\n完成：共 ' + calls.length + ' 次 fetch（皆為模擬）');
})().catch(e => { console.error('測試異常：', e); process.exit(1); });
