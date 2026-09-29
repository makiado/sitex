(function(){
  const sources = {
    leaflet: [
      'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
      'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js'
    ],
    d3: [
      'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js',
      'https://d3js.org/d3.v7.min.js'
    ],
    topojson: [
      'https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js',
      'https://unpkg.com/topojson-client@3/dist/topojson-client.min.js'
    ]
  };
  function loadOne(url){
    return new Promise((resolve,reject)=>{
      const s=document.createElement('script'); s.src=url; s.async=false;
      s.onload=()=>resolve(url); s.onerror=()=>reject(new Error(url));
      document.head.appendChild(s);
    });
  }
  async function loadAny(list){
    for(const url of list){
      try { await loadOne(url); return true; } catch(e) { console.warn('Falha ao carregar biblioteca:',url); }
    }
    return false;
  }
  (async()=>{
    await loadAny(sources.leaflet);
    await loadAny(sources.d3);
    await loadAny(sources.topojson);
    const app=document.createElement('script');
    app.src='js/app.js?v=3.0';
    app.onload=()=>window.dispatchEvent(new Event('memorias-app-ready'));
    app.onerror=()=>{
      const status=document.getElementById('statusText');
      if(status) status.textContent='Não foi possível carregar o aplicativo.';
    };
    document.body.appendChild(app);
  })();
})();
