// OmniVault Shop: starter brand directory + local, user-scoped discovery preferences.
// Starter entries are editorial links, NOT a live product inventory or retailer affiliation.
const STARTER = [{"id": "starter-0", "name": "Nike", "category": "Sneakers", "url": "https://www.nike.com", "mark": "N", "tone": "orange"}, {"id": "starter-1", "name": "Adidas", "category": "Sneakers", "url": "https://www.adidas.com", "mark": "A", "tone": "black"}, {"id": "starter-2", "name": "New Balance", "category": "Sneakers", "url": "https://www.newbalance.com", "mark": "NB", "tone": "red"}, {"id": "starter-3", "name": "ASICS", "category": "Sneakers", "url": "https://www.asics.com", "mark": "AS", "tone": "blue"}, {"id": "starter-4", "name": "Converse", "category": "Sneakers", "url": "https://www.converse.com", "mark": "C", "tone": "black"}, {"id": "starter-5", "name": "Vans", "category": "Sneakers", "url": "https://www.vans.com", "mark": "V", "tone": "red"}, {"id": "starter-6", "name": "Uniqlo", "category": "Fashion", "url": "https://www.uniqlo.com", "mark": "U", "tone": "red"}, {"id": "starter-7", "name": "Zara", "category": "Fashion", "url": "https://www.zara.com", "mark": "Z", "tone": "black"}, {"id": "starter-8", "name": "H&M", "category": "Fashion", "url": "https://www.hm.com", "mark": "H", "tone": "red"}, {"id": "starter-9", "name": "Aritzia", "category": "Fashion", "url": "https://www.aritzia.com", "mark": "AR", "tone": "black"}, {"id": "starter-10", "name": "Levi’s", "category": "Fashion", "url": "https://www.levi.com", "mark": "L", "tone": "red"}, {"id": "starter-11", "name": "COS", "category": "Fashion", "url": "https://www.cos.com", "mark": "CO", "tone": "black"}, {"id": "starter-12", "name": "Stüssy", "category": "Streetwear", "url": "https://www.stussy.com", "mark": "ST", "tone": "purple"}, {"id": "starter-13", "name": "Carhartt WIP", "category": "Streetwear", "url": "https://us.carhartt-wip.com", "mark": "CW", "tone": "orange"}, {"id": "starter-14", "name": "Kith", "category": "Streetwear", "url": "https://kith.com", "mark": "K", "tone": "black"}, {"id": "starter-15", "name": "Supreme", "category": "Streetwear", "url": "https://us.supreme.com", "mark": "S", "tone": "red"}, {"id": "starter-16", "name": "Palace", "category": "Streetwear", "url": "https://www.palaceskateboards.com", "mark": "P", "tone": "blue"}, {"id": "starter-17", "name": "Fear of God", "category": "Streetwear", "url": "https://fearofgod.com", "mark": "FG", "tone": "tan"}, {"id": "starter-18", "name": "Apple", "category": "Tech", "url": "https://www.apple.com", "mark": "AP", "tone": "black"}, {"id": "starter-19", "name": "Sony", "category": "Tech", "url": "https://electronics.sony.com", "mark": "SO", "tone": "blue"}, {"id": "starter-20", "name": "Samsung", "category": "Tech", "url": "https://www.samsung.com", "mark": "SA", "tone": "blue"}, {"id": "starter-21", "name": "Bose", "category": "Tech", "url": "https://www.bose.com", "mark": "BO", "tone": "black"}, {"id": "starter-22", "name": "JBL", "category": "Tech", "url": "https://www.jbl.com", "mark": "JB", "tone": "orange"}, {"id": "starter-23", "name": "Logitech", "category": "Tech", "url": "https://www.logitech.com", "mark": "LO", "tone": "teal"}, {"id": "starter-24", "name": "IKEA", "category": "Home", "url": "https://www.ikea.com", "mark": "IK", "tone": "yellow"}, {"id": "starter-25", "name": "West Elm", "category": "Home", "url": "https://www.westelm.com", "mark": "WE", "tone": "tan"}, {"id": "starter-26", "name": "Crate & Barrel", "category": "Home", "url": "https://www.crateandbarrel.com", "mark": "CB", "tone": "black"}, {"id": "starter-27", "name": "Muji", "category": "Home", "url": "https://www.muji.us", "mark": "MU", "tone": "red"}, {"id": "starter-28", "name": "Brooklinen", "category": "Home", "url": "https://www.brooklinen.com", "mark": "BR", "tone": "blue"}, {"id": "starter-29", "name": "Parachute", "category": "Home", "url": "https://www.parachutehome.com", "mark": "PA", "tone": "tan"}, {"id": "starter-30", "name": "Sephora", "category": "Beauty", "url": "https://www.sephora.com", "mark": "SE", "tone": "black"}, {"id": "starter-31", "name": "Ulta Beauty", "category": "Beauty", "url": "https://www.ulta.com", "mark": "UL", "tone": "orange"}, {"id": "starter-32", "name": "Glossier", "category": "Beauty", "url": "https://www.glossier.com", "mark": "GL", "tone": "pink"}, {"id": "starter-33", "name": "The Ordinary", "category": "Beauty", "url": "https://theordinary.com", "mark": "TO", "tone": "black"}, {"id": "starter-34", "name": "Fenty Beauty", "category": "Beauty", "url": "https://fentybeauty.com", "mark": "FB", "tone": "pink"}, {"id": "starter-35", "name": "Rare Beauty", "category": "Beauty", "url": "https://www.rarebeauty.com", "mark": "RB", "tone": "pink"}, {"id": "starter-36", "name": "Lululemon", "category": "Activewear", "url": "https://shop.lululemon.com", "mark": "LL", "tone": "red"}, {"id": "starter-37", "name": "Gymshark", "category": "Activewear", "url": "https://www.gymshark.com", "mark": "GY", "tone": "black"}, {"id": "starter-38", "name": "Alo Yoga", "category": "Activewear", "url": "https://www.aloyoga.com", "mark": "ALO", "tone": "tan"}, {"id": "starter-39", "name": "Under Armour", "category": "Activewear", "url": "https://www.underarmour.com", "mark": "UA", "tone": "black"}, {"id": "starter-40", "name": "Patagonia", "category": "Activewear", "url": "https://www.patagonia.com", "mark": "PT", "tone": "blue"}, {"id": "starter-41", "name": "The North Face", "category": "Activewear", "url": "https://www.thenorthface.com", "mark": "NF", "tone": "red"}];
const CATEGORIES = ['For you','Saved','Sneakers','Fashion','Streetwear','Tech','Home','Beauty','Activewear'];
const enc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let filter = 'For you', search = '', page = 0;
const PAGE_SIZE = 18;
function accountKey() {
  try { const token = sessionStorage.getItem('ov_token'); const raw = token?.split('.')[1]; if (!raw) return 'guest';
    const claims = JSON.parse(atob(raw.replace(/-/g,'+').replace(/_/g,'/')));
    return String(claims.sub ?? claims.user_id ?? 'guest').replace(/[^a-zA-Z0-9_-]/g,'').slice(0,64);
  } catch { return 'guest'; }
}
function storageKey() { return 'omnivault-shop-v2-' + accountKey(); }
function load() { try { const v = JSON.parse(localStorage.getItem(storageKey()) || '{}'); return { saved:v.saved||{}, viewed:v.viewed||{}, categories:v.categories||{}, clicks:v.clicks||{} }; } catch { return {saved:{},viewed:{},categories:{},clicks:{}}; } }
function save(s) { try { localStorage.setItem(storageKey(),JSON.stringify(s)); } catch {} }
function score(b,s) {
  const affinity = Number(s.categories[b.category]||0);
  const saved = s.saved[b.id] ? 60 : 0;
  const clicks = Math.min(8, Number(s.clicks[b.id]||0))*7;
  // Seeded variety remains part of the feed even after preference learning.
  const variety = (Number(b.id.replace('starter-','')) * 17 + 11) % 23;
  return saved + clicks + affinity*5 + variety;
}
function tile(b,s) {
  const fav=!!s.saved[b.id];
  return `<article class="discover-card">
    <div class="discover-art tone-${enc(b.tone)}"><span class="discover-monogram">${enc(b.mark)}</span><span class="discover-category">${enc(b.category)}</span></div>
    <div class="discover-card-body"><div class="discover-card-title"><b>${enc(b.name)}</b><button class="discover-save ${fav?'active':''}" type="button" data-shop-action="save" data-shop-id="${enc(b.id)}" aria-label="${fav?'Remove '+enc(b.name)+' from saved':'Save '+enc(b.name)}" aria-pressed="${fav}">${fav?'♥':'♡'}</button></div>
    <div class="discover-card-bottom"><span>${enc(b.category)}</span><a class="discover-link" href="${enc(b.url)}" target="_blank" rel="noopener noreferrer" data-shop-action="visit" data-shop-id="${enc(b.id)}">Explore ↗</a></div></div></article>`;
}
function curated(s) {
  let found=STARTER.filter(b => (filter==='For you'||filter==='Saved'||b.category===filter) && (filter!=='Saved'||s.saved[b.id]));
  if(search) found=found.filter(b => (b.name+' '+b.category).toLowerCase().includes(search.toLowerCase()));
  return found.sort((a,b)=>score(b,s)-score(a,s));
}
export function renderShop() {
  const s=load(); const found=curated(s); const visible=found.slice(0,(page+1)*PAGE_SIZE);
  const favorites=Object.keys(s.saved).filter(k=>s.saved[k]).length;
  const recent=Object.values(s.clicks).reduce((a,b)=>a+Number(b||0),0);
  return `<section class="discover" aria-label="Shop discovery">
    <div class="discover-hero"><div><span class="discover-eyebrow">OMNIVAULT DISCOVER</span><h2>Find your next favorite.</h2><p>Explore brands across fashion, tech, home and more. Your feed learns from what you save and explore.</p><div class="discover-hero-tags"><span>✦ Made for your taste</span><span>◈ Discover something new</span></div></div><div class="discover-hero-symbol" aria-hidden="true">✳</div></div>
    <div class="discover-toolbar"><label class="discover-search"><span aria-hidden="true">⌕</span><input id="shopSearch" type="search" placeholder="Search brands or categories" value="${enc(search)}" aria-label="Search brands or categories"></label><div class="discover-meta">${favorites} saved · ${recent} visits</div></div>
    <div class="discover-filters" role="group" aria-label="Shop categories">${CATEGORIES.map(c=>`<button type="button" class="discover-filter ${filter===c?'selected':''}" data-shop-action="filter" data-shop-category="${enc(c)}" aria-pressed="${filter===c}">${c==='Saved'?'♥ ':''}${enc(c)}</button>`).join('')}</div>
    <div class="discover-heading"><div><h3>${filter==='For you'?'Discover for you':filter==='Saved'?'Your saved brands':enc(filter)}</h3><p>${filter==='For you'?'A changing mix of popular brands and your interests':filter==='Saved'?'Brands you want to revisit':'Explore brands in this category'}</p></div><span>${found.length} brands</span></div>
    ${found.length?`<div class="discover-grid">${visible.map(b=>tile(b,s)).join('')}</div>${visible.length<found.length?'<div class="discover-more"><button type="button" class="btn ghost" data-shop-action="more">Show more brands</button></div>':''}`:`<div class="discover-empty"><strong>Nothing here yet</strong><p>${filter==='Saved'?'Tap a heart on any brand to save it.':'Try a different search or category.'}</p><button type="button" class="btn ghost" data-shop-action="reset">Explore all brands</button></div>`}
    <div class="discover-footer">Starter brand directory for discovery. External links go to brand websites. OmniVault does not provide live prices, inventory, retailer partnerships, or product purchases in this version. Preferences are stored in this browser.</div>
  </section>`;
}
export function bindShop() {
  const root=document.querySelector('.discover'); if(!root) return;
  const redraw=()=>{ const view=document.querySelector('#view'); if(view){view.innerHTML=renderShop();bindShop();} };
  const field=root.querySelector('#shopSearch');
  field?.addEventListener('input',()=>{
    search=field.value;page=0;
    const s=load(),found=curated(s);
    const area=root.querySelector('.discover-grid, .discover-empty');
    if(area) {const holder=document.createElement('div');holder.innerHTML=found.length?`<div class="discover-grid">${found.slice(0,PAGE_SIZE).map(b=>tile(b,s)).join('')}</div>`:`<div class="discover-empty"><strong>No matches</strong><p>Try another search.</p></div>`;area.replaceWith(holder.firstElementChild);}
    const h=root.querySelector('.discover-heading span');if(h)h.textContent=found.length+' brands';
    root.querySelector('.discover-more')?.remove();
  });
  root.addEventListener('click',e=>{
    const btn=e.target.closest('[data-shop-action]');if(!btn)return;
    const action=btn.dataset.shopAction, id=btn.dataset.shopId;
    if(action==='filter'){filter=btn.dataset.shopCategory;search='';page=0;redraw();return;}
    if(action==='reset'){filter='For you';search='';page=0;redraw();return;}
    if(action==='more'){page++;redraw();return;}
    const b=STARTER.find(x=>x.id===id);if(!b)return;
    const s=load();
    if(action==='save') {s.saved[id]=!s.saved[id];s.categories[b.category]=Math.max(0,Number(s.categories[b.category]||0)+(s.saved[id]?3:-3));save(s);redraw();}
    if(action==='visit'){s.clicks[id]=Math.min(100,Number(s.clicks[id]||0)+1);s.categories[b.category]=Math.min(100,Number(s.categories[b.category]||0)+1);save(s);}
  });
}
