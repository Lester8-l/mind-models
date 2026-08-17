/* 建置思维模型手册：template_ref.html + parts/* → 思维模型手册.html
   資料檔 data.js 只在不存在（或帶 --force-data）時才從參考檔重新產生，
   避免覆蓋掉你在網頁裡編輯過的內容。 */
const fs = require('fs');
const FORCE = process.argv.includes('--force-data');
const SRC = 'C:/Users/Jason/Downloads/index.html';

/* ---------- 1. data.js ---------- */
if (!fs.existsSync('data.js') || FORCE) {
  const html = fs.readFileSync(SRC, 'utf8');
  const code = html.slice(html.indexOf('const CATS'), html.indexOf('];', html.indexOf('const MODELS')) + 2);
  const { CATS, MODELS } = new Function(code + '\nreturn {CATS, MODELS};')();
  if (fs.existsSync('data.js')) fs.copyFileSync('data.js', 'data_backup.js');
  fs.writeFileSync('data.js',
    '// 思维模型数据 · 来源：B站「檀東東Tango」《100個思維模型》合集转写整理\n' +
    '// 修改内容只需编辑此文件并刷新页面，无需改动 handbook。\n' +
    'const CATS = ' + JSON.stringify(CATS, null, 2) + ';\n\n' +
    'const MODELS = ' + JSON.stringify(MODELS, null, 2) + ';\n');
  console.log('已重新產生 data.js | 模型數:', MODELS.length);
} else {
  const { MODELS } = new Function(fs.readFileSync('data.js', 'utf8') + '\nreturn {CATS, MODELS};')();
  console.log('保留現有 data.js（模型數:', MODELS.length, '）— 需重建請加 --force-data');
}

/* ---------- 2. 注入編輯層並輸出 handbook ---------- */
const css = fs.readFileSync('parts/editor.css', 'utf8');
const js = ['parts/editor_edit.js', 'parts/editor_sync.js']
  .map(f => '<script>\n' + fs.readFileSync(f, 'utf8') + '</script>')
  .join('\n');

const out = fs.readFileSync('template_ref.html', 'utf8')
  .replace('/*__EDITOR_CSS__*/', css)
  .replace('<!--__EDITOR_JS__-->', js);

if (out.includes('__EDITOR_CSS__') || out.includes('__EDITOR_JS__')) {
  console.error('✗ 佔位符未被替換，請檢查 template_ref.html');
  process.exit(1);
}

const OUT = '思维模型手册.html';
if (fs.existsSync(OUT)) fs.copyFileSync(OUT, '思维模型手册_backup.html');
fs.writeFileSync(OUT, out);
fs.writeFileSync('index.html', out);   // 給 GitHub / 靜態託管用（與 data.js 同目錄）
console.log('已生成', OUT, '+ index.html | 大小', (out.length / 1024).toFixed(1), 'KB（資料來自同目錄 data.js）');
