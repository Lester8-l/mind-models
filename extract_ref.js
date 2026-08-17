const fs = require('fs');
const SRC = 'C:/Users/Jason/Downloads/index.html';
const html = fs.readFileSync(SRC, 'utf8');

// 抓取 const CATS = {...}; 与 const MODELS = [...]; 两段
const catStart = html.indexOf('const CATS');
const modelStart = html.indexOf('const MODELS');
const modelEnd = html.indexOf('];', modelStart);
const code = html.slice(catStart, modelEnd + 2); // 含结尾 ];

const fn = new Function(code + '\nreturn {CATS, MODELS};');
const { CATS, MODELS } = fn();

// 字段完整性检查
const fields = ['no','name','cat','tag','bv','thought','points','scenes','explain','extend','tips','related'];
let missing = 0;
MODELS.forEach(m => {
  fields.forEach(f => { if (m[f] === undefined) { missing++; /* console.log('MISS', m.no, f); */ } });
});

console.log('CATS:', Object.keys(CATS).join(' / '));
console.log('MODELS count:', MODELS.length);
console.log('missing fields total:', missing);
console.log('sample no list (first 5):', MODELS.slice(0,5).map(m=>m.no).join(','));
console.log('last 3:', MODELS.slice(-3).map(m=>m.no+' '+m.name).join(' | '));
console.log('categories distribution:',
  Object.keys(CATS).map(c => c+':'+MODELS.filter(m=>m.cat===c).length).join('  '));

fs.writeFileSync('extracted_ref.json', JSON.stringify({CATS, MODELS}, null, 0));
console.log('written extracted_ref.json');
