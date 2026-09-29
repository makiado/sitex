const state={catalog:null,country:null,region:null,year:null,countryMap:null,countryLayer:null,isoNumeric:null};
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function normalizeCountry(v){return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');}
const COUNTRY_ALIASES={
  brasil:'BR', brazil:'BR',
  estadosunidos:'US', unitedstates:'US',
  reinounido:'GB', unitedkingdom:'GB',
  russia:'RU', 'federacaorussa':'RU',
  coreiadosul:'KR', southkorea:'KR',
  republicatcheca:'CZ', czechia:'CZ',
  eslovaquia:'SK', slovenia:'SI',
  holanda:'NL', paisesbaixos:'NL', netherlands:'NL'
};

async function loadJson(url){
  try{
    const r=await fetch(url,{cache:'no-store'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    return await r.json();
  }catch(fetchErr){
    return await new Promise((resolve,reject)=>{
      const xhr=new XMLHttpRequest();
      xhr.open('GET',url,true); xhr.responseType='json';
      xhr.onload=()=>xhr.status>=200&&xhr.status<300?resolve(xhr.response):reject(fetchErr);
      xhr.onerror=()=>reject(fetchErr);
      xhr.send();
    });
  }
}

async function loadJsonAny(urls){
  for(const url of urls){try{return await loadJson(url);}catch(e){console.warn('Falha ao carregar',url,e)}}
  throw new Error('Todos os endereços falharam');
}

async function loadCatalog(){
  try{
    state.catalog=await loadJson('../data/photos.json?'+Date.now());
    state.catalog.photos=Array.isArray(state.catalog.photos)?state.catalog.photos:[];
    const iso=await loadJson('../site/assets/iso2_to_numeric.json').catch(()=>({}));
    state.isoNumeric=iso||{};
    renderStats(); renderWorld();
    $('#statusText').textContent=`${state.catalog.photos.length} fotografias catalogadas`;
  }catch(e){
    $('#statusText').textContent='Erro ao ler o catálogo. Execute o servidor pelo abrir_site.bat.';
    console.error(e);
  }
}
function renderStats(){
 const c=state.catalog;
 $('#stats').innerHTML=[
  ['fotografias',c.photos.length],['países',c.countries?.length||0],['estados / regiões',c.states?.length||0],['anos',c.years?.length||0]
 ].map(x=>`<div class="stat"><strong>${x[1]}</strong><span>${x[0]}</span></div>`).join('');
}
function countryRecords(){return state.catalog.photos.filter(p=>p.country===state.country)}
function countryCodeFromName(name){return COUNTRY_ALIASES[normalizeCountry(name)]||null}

function renderWorldFallback(reason=''){
 const el=$('#worldMap');
 const countries=[...new Set(state.catalog.photos.map(p=>p.country).filter(Boolean))].sort();
 el.innerHTML=`<div class="world-fallback"><div class="fallback-title">Mapa mundial indisponível nesta sessão</div><div class="fallback-sub">${esc(reason||'O navegador bloqueou um dos recursos geográficos externos. As suas fotos continuam funcionando normalmente.')}</div><div class="fallback-countries">${countries.map(c=>`<button class="fallback-country" data-fallback-country="${esc(c)}">${esc(c)}<span>${state.catalog.photos.filter(p=>p.country===c).length}</span></button>`).join('')}</div></div>`;
 document.querySelectorAll('[data-fallback-country]').forEach(b=>b.onclick=()=>openCountry(b.dataset.fallbackCountry));
}

async function renderWorld(){
 const el=window.d3?.select?window.d3.select('#worldMap'):null;
 if(!el || !window.d3 || !window.topojson){
   renderWorldFallback('A biblioteca do mapa não foi carregada.'); return;
 }
 el.selectAll('*').remove();
 const w=el.node().clientWidth||1100,h=el.node().clientHeight||560;
 const svg=el.append('svg').attr('viewBox',`0 0 ${w} ${h}`).attr('width','100%').attr('height','100%');
 const g=svg.append('g');
 const projection=window.d3.geoNaturalEarth1().fitExtent([[20,20],[w-20,h-20]],{type:'Sphere'});
 const path=window.d3.geoPath(projection);
 let world;
 try{world=await loadJsonAny([
   'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json',
   'https://unpkg.com/world-atlas@2/countries-110m.json',
   'https://fastly.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
 ]);}catch(e){renderWorldFallback('Os dados geográficos externos não puderam ser carregados.');return;}
 const countries=topojson.feature(world,world.objects.countries).features;
 const activeCodes=new Set((state.catalog.photos||[]).map(p=>String(p.country_code||'').toUpperCase()).filter(Boolean));
 const activeNames=new Set((state.catalog.countries||[]).map(normalizeCountry));
 const numeric=state.isoNumeric||{};
 const numericToIso={}; for(const [iso,num] of Object.entries(numeric)){numericToIso[String(num).padStart(3,'0')]=iso;}
 g.selectAll('path').data(countries).join('path')
  .attr('d',path).attr('class',d=>{
    const id=String(d.id).padStart(3,'0');
    const cc=numericToIso[id];
    const featureName=normalizeCountry(d.properties?.name);
    const aliasCode=countryCodeFromName(d.properties?.name);
    const active=(cc&&activeCodes.has(cc)) || (aliasCode&&activeCodes.has(aliasCode)) || activeNames.has(featureName) || (aliasCode && activeNames.has(normalizeCountry('Brasil'))&&aliasCode==='BR');
    return 'world-country '+(active?'active':'inactive');
  })
  .on('click',(ev,d)=>{
    const id=String(d.id).padStart(3,'0');
    const cc=numericToIso[id] || countryCodeFromName(d.properties?.name);
    const match=state.catalog.photos.find(p=>(cc&&String(p.country_code||'').toUpperCase()===cc)||normalizeCountry(p.country)===normalizeCountry(d.properties?.name)||normalizeCountry(p.country)==='brasil'&&cc==='BR');
    if(match) openCountry(match.country);
  });
}
function openCountry(country){
 closeLightbox();
 state.country=country; state.region=null; state.year=null;
 $('#worldSection').hidden=true; $('#countrySection').hidden=false;
 renderCountry(); window.scrollTo({top:0,behavior:'smooth'});
}
function renderCountry(){
 const rows=countryRecords();
 const years=[...new Set(rows.map(p=>p.year).filter(Boolean))].sort((a,b)=>b-a);
 const regions=[...new Set(rows.map(p=>p.state).filter(Boolean))].sort();
 $('#countryTitle').textContent=state.country;
 const code=rows[0]?.country_code||'';
 $('#countryMeta').textContent=`${rows.length} fotografias · ${regions.length} regiões · ${years.length} anos${code?' · '+code:''}`;
 $('#regionList').innerHTML=regions.map(r=>`<button class="region-btn ${state.region===r?'active':''}" data-region="${esc(r)}"><span>${esc(r)}</span><span class="count">${rows.filter(p=>p.state===r).length}</span></button>`).join('')||'<div class="photo-sub">Nenhuma região identificada.</div>';
 $('#yearList').innerHTML=years.map(y=>`<button class="year-btn ${state.year===y?'active':''}" data-year="${y}"><span>${y}</span><span class="count">${rows.filter(p=>p.year===y).length}</span></button>`).join('');
 $('#filters').innerHTML=`<button class="chip ${!state.region?'active':''}" data-filter="region-all">Todas as regiões</button><button class="chip ${!state.year?'active':''}" data-filter="year-all">Todos os anos</button>`;
 document.querySelectorAll('[data-region]').forEach(b=>b.onclick=()=>{state.region=b.dataset.region;renderCountry();});
 document.querySelectorAll('[data-year]').forEach(b=>b.onclick=()=>{state.year=Number(b.dataset.year);renderCountry();});
 document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{if(b.dataset.filter==='region-all')state.region=null;else state.year=null;renderCountry();});
 renderCountryMap(rows); renderFeed();
}
async function renderCountryMap(rows){
 if(state.countryMap){try{state.countryMap.remove();}catch{} state.countryMap=null;}
 if(state.countryLayer){try{state.countryLayer.remove();}catch{} state.countryLayer=null;}
 const card=$('#countryMap');
 const pts=rows.filter(p=>p.latitude!=null&&p.longitude!=null);
 if(!window.L){
   card.innerHTML=`<div class="map-fallback"><div class="fallback-title">Mapa detalhado indisponível</div><div class="fallback-sub">${pts.length} ponto(s) com coordenadas foram encontrados.</div><div class="coord-list">${pts.slice(0,30).map(p=>`<div><strong>${esc(p.city||p.state||p.country||'Local')}</strong><span>${Number(p.latitude).toFixed(5)}, ${Number(p.longitude).toFixed(5)}</span></div>`).join('')}</div></div>`;
   $('#mapNote').textContent='Os pontos e fotografias continuam disponíveis abaixo.';
   return;
 }
 const map=L.map('countryMap',{zoomControl:true,attributionControl:false}).setView(pts[0]?[pts[0].latitude,pts[0].longitude]:[0,0],pts.length?4:2);
 state.countryMap=map;
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(map);
 if(pts.length){const group=[];for(const p of pts){const mk=L.circleMarker([p.latitude,p.longitude],{radius:6,color:'#f3c96b',weight:1,fillOpacity:.75}).addTo(map);mk.bindPopup(`<strong>${esc(p.city||p.state||p.country||'Local')}</strong><br>${formatDate(p.date)}`);group.push(mk)};map.fitBounds(L.featureGroup(group).getBounds().pad(.18));}
 const iso2=String(rows[0]?.country_code||'').toUpperCase();
 const iso3=(await loadJson('../site/assets/iso2_to_iso3.json').catch(()=>({})))[iso2];
 let loaded=false;
 if(iso3){try{
   const meta=await loadJsonAny([`https://www.geoboundaries.org/api/current/gbOpen/${iso3}/ADM1/`]);
   const gj=await loadJsonAny([meta.gjDownloadURL]);
   state.countryLayer=L.geoJSON(gj,{style:f=>({color:'#697183',weight:1,fillColor:'#252b37',fillOpacity:.42}),onEachFeature:(f,l)=>{const props=f.properties||{};const name=props.shapeName||props.name||props.NAME_1||'Região';l.on('click',()=>{const match=regionsName(rows,name);if(match){state.region=match;renderCountry();}});l.bindTooltip(name,{sticky:true});}}).addTo(map); loaded=true;
   $('#mapNote').textContent='Clique em uma divisão no mapa ou use a lista à esquerda.';
 }catch(e){} }
 if(!loaded) $('#mapNote').textContent=pts.length?'Mapa de pontos; limites administrativos indisponíveis.':'Sem coordenadas para mapear.';
}
function regionsName(rows,name){const norm=normalizeCountry(name);return [...new Set(rows.map(p=>p.state).filter(Boolean))].find(s=>normalizeCountry(s)===norm)||null;}
function renderFeed(){
 let rows=countryRecords();
 if(state.region)rows=rows.filter(p=>p.state===state.region);
 if(state.year)rows=rows.filter(p=>p.year===state.year);
 rows.sort((a,b)=>(b.date||'').localeCompare(a.date||''));
 $('#feedTitle').textContent=state.region?`${state.region} · ${state.year||'todos os anos'}`:`Todas as fotografias${state.year?' · '+state.year:''}`;
 $('#resultCount').textContent=`${rows.length} ${rows.length===1?'foto':'fotos'}`;
 $('#feed').innerHTML=rows.map(p=>`<article class="photo-card"><img class="photo-image" src="${esc(p.path)}" alt="${esc(p.filename)}" loading="lazy" data-full="${esc(p.path)}"><div class="photo-info"><div><div class="photo-title">${esc(p.city||p.state||p.country||'Sem local')}</div><div class="photo-sub">${esc(p.state||'')}${p.state&&p.country?', ':''}${esc(p.country||'')}</div></div><div class="photo-date">${formatDate(p.date)}</div></div></article>`).join('')||'<div class="photo-sub">Nenhuma fotografia corresponde aos filtros selecionados.</div>';
 document.querySelectorAll('.photo-image').forEach(img=>img.onclick=()=>openLightbox(img.dataset.full,img.alt));
}
function formatDate(s){if(!s)return 'Data desconhecida';const d=new Date(s);return isNaN(d)?String(s):d.toLocaleDateString('pt-BR',{day:'2-digit',month:'long',year:'numeric'});}
function openLightbox(src,alt=''){const box=$('#lightbox'),img=$('#lightboxImg');img.alt=alt||'';img.src=src;box.hidden=false;box.classList.add('is-open');box.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';}
function closeLightbox(){const box=$('#lightbox'),img=$('#lightboxImg');box.classList.remove('is-open');box.hidden=true;box.setAttribute('aria-hidden','true');img.removeAttribute('src');document.body.style.overflow='';}
function backToWorld(){closeLightbox();$('#countrySection').hidden=true;$('#worldSection').hidden=false;state.country=null;state.region=null;state.year=null;window.scrollTo({top:0,behavior:'smooth'});setTimeout(()=>renderWorld(),0);}
$('#backBtn').onclick=backToWorld;
$('#resetBtn').onclick=backToWorld;
$('#lightboxClose').onclick=closeLightbox;
$('#lightbox').onclick=e=>{if(e.target.id==='lightbox')closeLightbox()};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeLightbox()});
$('#lightboxImg').addEventListener('error',()=>{closeLightbox();console.warn('Imagem não pôde ser carregada:',$('#lightboxImg').alt)});
window.addEventListener('resize',()=>{if(state.catalog&&!$('#worldSection').hidden){clearTimeout(window.__mapResizeTimer);window.__mapResizeTimer=setTimeout(renderWorld,250)}});
closeLightbox();
loadCatalog();
