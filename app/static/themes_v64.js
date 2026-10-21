(()=>{"use strict";
const THEMES=[{"id":"fruit-001","name":"Strawberry","category":"Fruit","bg":"#240d13","bg2":"#38121c","panel":"#49202a","text":"#fff9f2","muted":"#d2b7be","accent":"#fe4977","accent2":"#a91645"},{"id":"fruit-002","name":"Raspberry","category":"Fruit","bg":"#240d15","bg2":"#38121f","panel":"#49202e","text":"#fff9f2","muted":"#d2b7c0","accent":"#ec3976","accent2":"#84204f"},{"id":"fruit-003","name":"Blueberry","category":"Fruit","bg":"#0d1424","bg2":"#121e38","panel":"#202c49","text":"#fff9f2","muted":"#b7bfd2","accent":"#5589ff","accent2":"#333d8f"},{"id":"fruit-004","name":"Blackberry","category":"Fruit","bg":"#170d24","bg2":"#241238","panel":"#332049","text":"#fff9f2","muted":"#c3b7d2","accent":"#954de8","accent2":"#452168"},{"id":"fruit-005","name":"Cherry","category":"Fruit","bg":"#240d11","bg2":"#381219","panel":"#492027","text":"#fff9f2","muted":"#d2b7bc","accent":"#ee3153","accent2":"#8a1233"},{"id":"fruit-006","name":"Peach","category":"Fruit","bg":"#24160d","bg2":"#382112","panel":"#493020","text":"#fff9f2","muted":"#d2c2b7","accent":"#ffab73","accent2":"#ff6877"},{"id":"fruit-007","name":"Mango","category":"Fruit","bg":"#241d0d","bg2":"#382d12","panel":"#493c20","text":"#fff9f2","muted":"#d2cab7","accent":"#ffbf2a","accent2":"#f36d21"},{"id":"fruit-008","name":"Pineapple","category":"Fruit","bg":"#241f0d","bg2":"#383012","panel":"#494120","text":"#fff9f2","muted":"#d2cdb7","accent":"#f4d34d","accent2":"#52a859"},{"id":"fruit-009","name":"Watermelon","category":"Fruit","bg":"#240d11","bg2":"#381219","panel":"#492027","text":"#fff9f2","muted":"#d2b7bc","accent":"#ff5875","accent2":"#26aa80"},{"id":"fruit-010","name":"Kiwi","category":"Fruit","bg":"#1a240d","bg2":"#293812","panel":"#384920","text":"#fff9f2","muted":"#c7d2b7","accent":"#a4d35e","accent2":"#4c9439"},{"id":"fruit-011","name":"Lime","category":"Fruit","bg":"#1a240d","bg2":"#273812","panel":"#374920","text":"#fff9f2","muted":"#c6d2b7","accent":"#a8f34a","accent2":"#4cba61"},{"id":"fruit-012","name":"Lemon","category":"Fruit","bg":"#24210d","bg2":"#383412","panel":"#494420","text":"#fff9f2","muted":"#d2cfb7","accent":"#fbea57","accent2":"#e4a831"},{"id":"fruit-013","name":"Orange","category":"Fruit","bg":"#24180d","bg2":"#382412","panel":"#493320","text":"#fff9f2","muted":"#d2c4b7","accent":"#ff9434","accent2":"#e94e42"},{"id":"fruit-014","name":"Grapefruit","category":"Fruit","bg":"#240d10","bg2":"#381218","panel":"#492026","text":"#fff9f2","muted":"#d2b7bb","accent":"#ff7388","accent2":"#ffa15e"},{"id":"fruit-015","name":"Pomegranate","category":"Fruit","bg":"#240d11","bg2":"#381218","panel":"#492026","text":"#fff9f2","muted":"#d2b7bb","accent":"#e23b56","accent2":"#74153b"},{"id":"fruit-016","name":"Dragon Fruit","category":"Fruit","bg":"#240d1c","bg2":"#38122b","panel":"#49203a","text":"#fff9f2","muted":"#d2b7c8","accent":"#f54dba","accent2":"#5bbc86"},{"id":"fruit-017","name":"Passion Fruit","category":"Fruit","bg":"#1d0d24","bg2":"#2c1238","panel":"#3c2049","text":"#fff9f2","muted":"#cab7d2","accent":"#d38bf2","accent2":"#fab44c"},{"id":"fruit-018","name":"Papaya","category":"Fruit","bg":"#24160d","bg2":"#382212","panel":"#493120","text":"#fff9f2","muted":"#d2c2b7","accent":"#ff9c54","accent2":"#ec5762"},{"id":"fruit-019","name":"Guava","category":"Fruit","bg":"#240d14","bg2":"#38121e","panel":"#49202c","text":"#fff9f2","muted":"#d2b7bf","accent":"#ff82a8","accent2":"#6ab86c"},{"id":"fruit-020","name":"Lychee","category":"Fruit","bg":"#240d13","bg2":"#38121c","panel":"#49202b","text":"#fff9f2","muted":"#d2b7be","accent":"#ed9bb1","accent2":"#bf4c78"},{"id":"fruit-021","name":"Coconut","category":"Fruit","bg":"#241b0d","bg2":"#382912","panel":"#493920","text":"#fff9f2","muted":"#d2c8b7","accent":"#bba98c","accent2":"#6f915f"},{"id":"fruit-022","name":"Fig","category":"Fruit","bg":"#1a0d24","bg2":"#281238","panel":"#382049","text":"#fff9f2","muted":"#c7b7d2","accent":"#ae75d7","accent2":"#67417f"},{"id":"fruit-023","name":"Plum","category":"Fruit","bg":"#230d24","bg2":"#371238","panel":"#482049","text":"#fff9f2","muted":"#d2b7d2","accent":"#ba59bb","accent2":"#572961"},{"id":"fruit-024","name":"Apricot","category":"Fruit","bg":"#24170d","bg2":"#382412","panel":"#493320","text":"#fff9f2","muted":"#d2c3b7","accent":"#fdb16f","accent2":"#fb734e"},{"id":"fruit-025","name":"Nectarine","category":"Fruit","bg":"#24140d","bg2":"#381e12","panel":"#492c20","text":"#fff9f2","muted":"#d2bfb7","accent":"#f39267","accent2":"#d64c6a"},{"id":"fruit-026","name":"Pear","category":"Fruit","bg":"#21240d","bg2":"#333812","panel":"#434920","text":"#fff9f2","muted":"#ced2b7","accent":"#c8d66b","accent2":"#65a56e"},{"id":"fruit-027","name":"Green Apple","category":"Fruit","bg":"#15240d","bg2":"#203812","panel":"#2e4920","text":"#fff9f2","muted":"#c1d2b7","accent":"#8ee65d","accent2":"#38a45d"},{"id":"fruit-028","name":"Red Apple","category":"Fruit","bg":"#240d0e","bg2":"#381214","panel":"#492022","text":"#fff9f2","muted":"#d2b7b9","accent":"#e9454f","accent2":"#79aa45"},{"id":"fruit-029","name":"Grape","category":"Fruit","bg":"#120d24","bg2":"#1b1238","panel":"#2a2049","text":"#fff9f2","muted":"#beb7d2","accent":"#9e80f9","accent2":"#5948a6"},{"id":"fruit-030","name":"Cantaloupe","category":"Fruit","bg":"#241a0d","bg2":"#382812","panel":"#493720","text":"#fff9f2","muted":"#d2c6b7","accent":"#ffc77b","accent2":"#7fba65"},{"id":"fruit-031","name":"Honeydew","category":"Fruit","bg":"#17240d","bg2":"#233812","panel":"#324920","text":"#fff9f2","muted":"#c3d2b7","accent":"#c2eaa1","accent2":"#6ab79e"},{"id":"fruit-032","name":"Starfruit","category":"Fruit","bg":"#24220d","bg2":"#383512","panel":"#494520","text":"#fff9f2","muted":"#d2d0b7","accent":"#e9de5c","accent2":"#79b462"},{"id":"fruit-033","name":"Persimmon","category":"Fruit","bg":"#24160d","bg2":"#382212","panel":"#493120","text":"#fff9f2","muted":"#d2c2b7","accent":"#ff964b","accent2":"#d54f31"},{"id":"fruit-034","name":"Tangerine","category":"Fruit","bg":"#241a0d","bg2":"#382812","panel":"#493820","text":"#fff9f2","muted":"#d2c7b7","accent":"#ffab35","accent2":"#ed6450"},{"id":"fruit-035","name":"Clementine","category":"Fruit","bg":"#241c0d","bg2":"#382b12","panel":"#493a20","text":"#fff9f2","muted":"#d2c8b7","accent":"#ffc04a","accent2":"#f27b4f"},{"id":"fruit-036","name":"Blood Orange","category":"Fruit","bg":"#240e0d","bg2":"#381412","panel":"#492220","text":"#fff9f2","muted":"#d2b8b7","accent":"#dd514b","accent2":"#8f2254"},{"id":"fruit-037","name":"Cranberry","category":"Fruit","bg":"#240d14","bg2":"#38121e","panel":"#49202c","text":"#fff9f2","muted":"#d2b7bf","accent":"#cf3766","accent2":"#781e4a"},{"id":"fruit-038","name":"Mulberry","category":"Fruit","bg":"#240d1e","bg2":"#38122e","panel":"#49203e","text":"#fff9f2","muted":"#d2b7cb","accent":"#af5b9a","accent2":"#473165"},{"id":"fruit-039","name":"Elderberry","category":"Fruit","bg":"#100d24","bg2":"#181238","panel":"#262049","text":"#fff9f2","muted":"#bbb7d2","accent":"#6c5eb7","accent2":"#44357f"},{"id":"fruit-040","name":"Acai","category":"Fruit","bg":"#160d24","bg2":"#221238","panel":"#312049","text":"#fff9f2","muted":"#c2b7d2","accent":"#8a60c3","accent2":"#492b71"},{"id":"fruit-041","name":"Jackfruit","category":"Fruit","bg":"#241e0d","bg2":"#382f12","panel":"#493f20","text":"#fff9f2","muted":"#d2ccb7","accent":"#e5c353","accent2":"#69934b"},{"id":"fruit-042","name":"Durian","category":"Fruit","bg":"#24220d","bg2":"#383512","panel":"#494620","text":"#fff9f2","muted":"#d2d0b7","accent":"#c8c15e","accent2":"#6d8744"},{"id":"fruit-043","name":"Soursop","category":"Fruit","bg":"#15240d","bg2":"#203812","panel":"#2f4920","text":"#fff9f2","muted":"#c1d2b7","accent":"#a8d98b","accent2":"#4b9868"},{"id":"fruit-044","name":"Tamarind","category":"Fruit","bg":"#24160d","bg2":"#382212","panel":"#493120","text":"#fff9f2","muted":"#d2c2b7","accent":"#b8794b","accent2":"#76472c"},{"id":"fruit-045","name":"Date Palm","category":"Fruit","bg":"#24170d","bg2":"#382212","panel":"#493220","text":"#fff9f2","muted":"#d2c3b7","accent":"#b88055","accent2":"#5d7044"},{"id":"fruit-046","name":"Olive Fruit","category":"Fruit","bg":"#22240d","bg2":"#363812","panel":"#464920","text":"#fff9f2","muted":"#d0d2b7","accent":"#c2c76a","accent2":"#626d42"},{"id":"fruit-047","name":"Kumquat","category":"Fruit","bg":"#241b0d","bg2":"#382912","panel":"#493920","text":"#fff9f2","muted":"#d2c7b7","accent":"#fcb64a","accent2":"#d97a29"},{"id":"fruit-048","name":"Yuzu","category":"Fruit","bg":"#23240d","bg2":"#373812","panel":"#474920","text":"#fff9f2","muted":"#d1d2b7","accent":"#e9ed68","accent2":"#77ad47"},{"id":"fruit-049","name":"Blackcurrant","category":"Fruit","bg":"#180d24","bg2":"#251238","panel":"#342049","text":"#fff9f2","muted":"#c4b7d2","accent":"#936db9","accent2":"#4c3b77"},{"id":"fruit-050","name":"Boysenberry","category":"Fruit","bg":"#240d1b","bg2":"#381229","panel":"#492039","text":"#fff9f2","muted":"#d2b7c7","accent":"#c45a9a","accent2":"#71356d"}];
const ICONS={"Strawberry":"🍓","Blueberry":"🫐","Cherry":"🍒","Peach":"🍑","Mango":"🥭","Pineapple":"🍍","Watermelon":"🍉","Kiwi":"🥝","Lime":"🍋‍🟩","Lemon":"🍋","Orange":"🍊","Coconut":"🥥","Pear":"🍐","Green Apple":"🍏","Red Apple":"🍎","Grape":"🍇"};

// FRUIT_STUDIO_2
const MODE_KEY='family-fruit-color-mode';
let fruitMode=localStorage.getItem(MODE_KEY)==='light'?'light':'dark';

// Fruit anatomy: skin, flesh, seeds, leaves and highlights.
// Overrides emphasize rare fruits with recognizable combinations.
const FRUIT_ANATOMY={
  "Dragon Fruit":["#ef2d99","#f7f3e9","#72bf74"],
  "Passion Fruit":["#59267d","#ffce40","#a875d6"],
  "Papaya":["#ef873b","#ffb45c","#398b58"],
  "Guava":["#f18daa","#ffd5dc","#78b76f"],
  "Lychee":["#ca526e","#fff0e5","#a6485c"],
  "Coconut":["#76513c","#fff2df","#baa48a"],
  "Fig":["#60336e","#db9aaf","#9aaf60"],
  "Starfruit":["#e6bc31","#fff0a0","#779e3d"],
  "Persimmon":["#db622c","#ffb04b","#55773c"],
  "Blood Orange":["#a92439","#f26c44","#e5ac58"],
  "Mulberry":["#512452","#a4528b","#718a49"],
  "Elderberry":["#32304f","#837cb3","#727d6d"],
  "Acai":["#47234e","#9870b3","#788a57"],
  "Jackfruit":["#d6aa32","#ffde73","#588842"],
  "Durian":["#87944b","#f5dfa0","#61723b"],
  "Soursop":["#74ab65","#f1f1ce","#326c43"],
  "Tamarind":["#815032","#cb9961","#63834b"],
  "Date Palm":["#79432d","#bb8052","#78834a"],
  "Olive Fruit":["#677447","#b5ad6b","#4d5736"],
  "Kumquat":["#ed952a","#ffd283","#5a9347"],
  "Yuzu":["#d5c83d","#f5ef8d","#789e47"],
  "Blackcurrant":["#382047","#9574ad","#627646"],
  "Boysenberry":["#692b58","#ca80a1","#637d4f"],
  "Rambutan":["#d93f55","#f1e7d5","#83aa46"]
};

function mixColor(a,b,t){
  const parse=x=>[1,3,5].map(i=>parseInt(x.slice(i,i+2),16));
  const A=parse(a),B=parse(b);
  return '#'+A.map((v,i)=>
    Math.round(v*(1-t)+B[i]*t)
      .toString(16).padStart(2,'0')
  ).join('');
}

function paletteFor(base){
  const anatomy=FRUIT_ANATOMY[base.name];
  const skin=anatomy?anatomy[0]:base.accent;
  const flesh=anatomy?anatomy[1]:base.accent2;
  const leaf=anatomy?anatomy[2]:base.accent2;

  if(fruitMode==='light'){
    return {
      ...base,
      bg:mixColor(flesh,'#ffffff',.91),
      bg2:mixColor(skin,'#ffffff',.85),
      panel:mixColor(flesh,'#ffffff',.82),
      text:'#282333',
      muted:'#665c6c',
      accent:mixColor(skin,'#252033',.18),
      accent2:mixColor(leaf,'#252033',.16),
      skin,flesh,leaf
    };
  }

  return {
    ...base,
    bg:mixColor(skin,'#080913',.88),
    bg2:mixColor(leaf,'#0b0c18',.83),
    panel:mixColor(skin,'#171622',.77),
    text:'#fff8fa',
    muted:'#d1c2d1',
    accent:mixColor(skin,'#ffffff',.16),
    accent2:mixColor(flesh,'#ffffff',.12),
    skin,flesh,leaf
  };
}

const KEY='family-v64-theme';
const byId=id=>THEMES.find(t=>t.id===id);
let current=localStorage.getItem(KEY);
if(!byId(current)) current=THEMES[0].id;
const fallbackGlyph=(t)=>{const label=t.name.replace(/[^a-zA-Z ]/g,'').split(' ');return label.length>1?label.map(w=>w[0]).join('').slice(0,2):label[0].slice(0,2);};
function iconHTML(t){const emoji=ICONS[t.name];return emoji?`<span class="fo64-fruit-emoji" aria-hidden="true">${emoji}</span>`:`<span class="fo64-fruit-vector" style="--fruit-rind:${t.accent2};--fruit-flesh:${t.accent}" aria-hidden="true"><span>${fallbackGlyph(t)}</span></span>`;}
function apply(id){const t=paletteFor(byId(id)||THEMES[0]);current=t.id;localStorage.setItem(KEY,current);const root=document.documentElement;
root.setAttribute('data-bs-theme',fruitMode);
root.setAttribute('data-fruit-mode',fruitMode);
root.style.setProperty('--bs-body-bg',t.bg);
root.style.setProperty('--bs-body-color',t.text);
root.style.setProperty('--bs-secondary-color',t.muted);
root.style.setProperty('--bs-border-color',t.accent2);
root.style.setProperty('--fo-rind',t.skin);
root.style.setProperty('--fo-flesh',t.flesh);
root.style.setProperty('--fo-leaf',t.leaf);

Object.entries({'--fo-bg':t.bg,'--fo-bg2':t.bg2,'--fo-panel':t.panel,'--fo-text':t.text,'--fo-muted':t.muted,'--fo-accent':t.accent,'--fo-accent2':t.accent2}).forEach(([k,v])=>root.style.setProperty(k,v));
root.style.setProperty('--fo-fruit-mark',`"${ICONS[t.name]||'🍃'}"`);
document.body?.classList.add('fo-fruit-active');
document.querySelectorAll('.fo64-theme').forEach(x=>x.classList.toggle('active',x.dataset.id===current));}
function mount(){if(document.querySelector('.fo64-launcher'))return;
const button=document.createElement('button');button.className='fo64-launcher';button.type='button';button.textContent='🍓';button.title='Choose Fruit Palette';button.setAttribute('aria-label','Open fruit palettes');
const panel=document.createElement('aside');panel.className='fo64-panel';panel.setAttribute('aria-label','Fruit palette studio');
panel.innerHTML=`<div class="d-flex justify-content-between align-items-center mb-3"><div><strong style="font-size:1.15rem">🍓 Fruit Palette Studio</strong><div class="small text-secondary">50 fruit-inspired color palettes • no unrelated themes</div></div><button type="button" class="btn btn-sm btn-outline-light" data-close aria-label="Close fruit palettes">✕</button></div><label class="visually-hidden" for="fruit-theme-search">Search fruit palettes</label><input id="fruit-theme-search" class="form-control mb-3" data-search placeholder="Search 50 fruit palettes"><div class="fruit-mode-controls" role="group" aria-label="Fruit color mode">
<button type="button" data-fruit-mode="light">☀️ Light</button>
<button type="button" data-fruit-mode="dark">🌙 Dark</button>
</div>
<div class="fo64-grid"></div>`;
document.body.append(button,panel);
const grid=panel.querySelector('.fo64-grid'),q=panel.querySelector('[data-search]');
function render(){
panel.querySelectorAll('[data-fruit-mode]').forEach(b=>{
 b.classList.toggle('active',b.dataset.fruitMode===fruitMode);
 b.setAttribute('aria-pressed',String(b.dataset.fruitMode===fruitMode));
});
const rows=THEMES.filter(t=>t.name.toLowerCase().includes(q.value.trim().toLowerCase()));grid.innerHTML=rows.map(raw=>{const t=paletteFor(raw);return `<button type="button" class="fo64-theme ${t.id===current?'active':''}" data-id="${t.id}"><div class="fo64-preview fo64-fruit-preview" style="background:linear-gradient(135deg,${t.bg},${t.accent2},${t.accent})">${iconHTML(t)}</div><strong>${t.name}</strong><span class="fo64-cat">Fruit palette</span></button>`;}).join('');grid.querySelectorAll('.fo64-theme').forEach(x=>x.onclick=()=>{apply(x.dataset.id);render();});}
panel.querySelectorAll('[data-fruit-mode]').forEach(b=>{
 b.addEventListener('click',()=>{
   fruitMode=b.dataset.fruitMode;
   localStorage.setItem(MODE_KEY,fruitMode);
   apply(current);
   render();
 });
});
const open=()=>{panel.classList.add('open');q.value='';render();};button.onclick=()=>panel.classList.toggle('open')?open():null;
const nav=document.getElementById('fo-fruit-themes-nav');if(nav)nav.onclick=open;
panel.querySelector('[data-close]').onclick=()=>panel.classList.remove('open');q.oninput=render;
apply(current);render();}
apply(current);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
