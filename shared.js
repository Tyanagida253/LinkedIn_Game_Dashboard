// Shared by index.html and player.html: constants, scoring, filters, small renderers.
const GAMES=["Queens","Tango","Zip","Mini Sudoku","Wend","Patches"];
const PLAYERS=["Tyler Yanagida","Oscar Gidley-Kitchin","Sophie Evans","Lucie Day"];
const HINT_PENALTY=60;
const MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const $=id=>document.getElementById(id);
const el=(t,txt,cls)=>{const e=document.createElement(t);if(txt!=null)e.textContent=txt;if(cls)e.className=cls;return e};
const fmt=s=>{const r=Math.round(s);return Math.floor(r/60)+":"+String(r%60).padStart(2,"0")};
const day=d=>Date.parse(d+"T00:00:00Z")/864e5;
const dlabel=n=>{const t=new Date(n*864e5);return MON[t.getUTCMonth()]+" "+t.getUTCDate()};
const eff=s=>s.timeSeconds+(s.hints?HINT_PENALTY:0); // time used for every comparison and average
const avg=a=>a.reduce((x,y)=>x+y,0)/a.length;
const pc=p=>"var(--p"+PLAYERS.indexOf(p)+")";
const ord=n=>n+(["th","st","nd","rd"][(n%100>10&&n%100<14)||n%10>3?0:n%10]);

// ---- filters: games (set) and range ("all" | "30" | "7"), kept in the URL and localStorage ----
const filters={games:new Set(GAMES),range:"all"};
(function(){
  const q=new URLSearchParams(location.search);let g=q.get("games"),r=q.get("range");
  try{g=g??localStorage.getItem("games");r=r??localStorage.getItem("range")}catch(e){}
  const list=(g||"").split(",").filter(x=>GAMES.includes(x));
  if(list.length)filters.games=new Set(list);
  if(["all","30","7"].includes(r))filters.range=r;
})();
function filterParams(){
  const q=new URLSearchParams();
  if(filters.games.size<GAMES.length)q.set("games",GAMES.filter(g=>filters.games.has(g)).join(","));
  if(filters.range!=="all")q.set("range",filters.range);
  return q;
}
function saveFilters(){
  const q=filterParams(),cur=new URLSearchParams(location.search),p=cur.get("p");
  if(p)q.set("p",p);
  history.replaceState(null,"",location.pathname+(q.toString()?"?"+q:""));
  try{localStorage.setItem("games",GAMES.filter(g=>filters.games.has(g)).join(","));localStorage.setItem("range",filters.range)}catch(e){}
}
function applyFilters(rows){
  if(!rows.length)return rows;
  const max=Math.max(...rows.map(s=>day(s.date))),n=filters.range==="all"?Infinity:+filters.range;
  return rows.filter(s=>filters.games.has(s.game)&&max-day(s.date)<n);
}
function filterBar(host,onChange){
  host.replaceChildren();
  const btn=(txt,on,fn)=>{const b=el("button",txt,"chip");b.type="button";b.setAttribute("aria-pressed",on);b.onclick=()=>{fn();saveFilters();filterBar(host,onChange);onChange()};return b};
  const g=el("div",null,"chips");g.setAttribute("role","group");g.setAttribute("aria-label","Games");
  g.append(btn("All games",filters.games.size===GAMES.length,()=>{filters.games=new Set(GAMES)}));
  GAMES.forEach(n=>g.append(btn(n,filters.games.size<GAMES.length&&filters.games.has(n),()=>{
    if(filters.games.size===GAMES.length)filters.games=new Set([n]);
    else{filters.games.has(n)?filters.games.delete(n):filters.games.add(n);if(!filters.games.size)filters.games=new Set(GAMES)}
  })));
  const r=el("div",null,"chips seg");r.setAttribute("role","group");r.setAttribute("aria-label","Date range");
  [["all","All time"],["30","Last 30 days"],["7","Last 7 days"]].forEach(([v,t])=>r.append(btn(t,filters.range===v,()=>{filters.range=v})));
  host.append(g,r);
}

// ---- scoring: rank each score within its (date, game) group; ties share a rank; groups of one are unranked ----
function ranked(rows){
  const g={},out=[];
  rows.forEach(s=>(g[s.date+"|"+s.game]=g[s.date+"|"+s.game]||[]).push(s));
  Object.values(g).forEach(a=>{
    const ts=a.map(eff);
    a.forEach(s=>out.push({...s,t:eff(s),n:a.length,rank:a.length<2?null:1+ts.filter(x=>x<eff(s)).length}));
  });
  return out;
}
function streaks(rows){ // consecutive days with any score
  const ds=[...new Set(rows.map(s=>day(s.date)))].sort((a,b)=>a-b);
  let best=0,run=0,prev=null;
  ds.forEach(d=>{run=prev!=null&&d===prev+1?run+1:1;best=Math.max(best,run);prev=d});
  return{cur:ds.length&&Math.floor(Date.now()/864e5)-prev<=1?run:0,longest:best};
}
function stats(rows){ // rows: ranked rows for one player
  const c=rows.filter(r=>r.rank),wins=c.filter(r=>r.rank===1).length;
  return{n:rows.length,contested:c.length,wins,
    rate:c.length?wins/c.length:null,pos:c.length?avg(c.map(r=>r.rank)):null,
    avg:rows.length?avg(rows.map(r=>r.t)):null,best:rows.length?Math.min(...rows.map(r=>r.t)):null,...streaks(rows)};
}

// ---- rendering helpers ----
function playerHref(p){const q=filterParams();q.set("p",p);return "player.html?"+q}
function who(p,link){
  const s=el(link?"a":"span",null,"who");if(link)s.href=playerHref(p);
  const d=el("span","","dot");d.style.background=pc(p);s.append(d,p);return s;
}
function table(host,heads,rows,empty,textCols=1){
  host.replaceChildren();
  if(!rows.length){host.append(el("p",empty,"empty"));return}
  const t=el("table"),tr=el("tr");
  heads.forEach((h,i)=>{const th=el("th",h,i<textCols?"":"n");th.scope="col";tr.append(th)});
  t.append(tr);
  rows.forEach(r=>{const tr=el("tr");r.forEach((c,i)=>{const td=el("td",null,i<textCols?"":"n");if(c instanceof Node)td.append(c);else td.textContent=c;tr.append(td)});t.append(tr)});
  host.append(t);
}
const NONE="–";
const hintNote=s=>s.hints?` (+${HINT_PENALTY}s hint = ${fmt(eff(s))})`:"";
const EMPTY="No scores in this range. Widen the date range or pick more games.";

// series: [{name,color,dash,pts:[{x:dayNumber,y:seconds,tip}]}]
function lineChart(host,series,label){
  host.replaceChildren();
  const pts=series.flatMap(s=>s.pts);
  if(pts.length<2){host.append(el("p","Needs at least two scores to draw a trend.","empty"));return}
  const W=520,H=250,L=44,R=14,T=12,B=28,xs=pts.map(p=>p.x),x0=Math.min(...xs),x1=Math.max(...xs),y1=Math.max(...pts.map(p=>p.y))*1.1,
    X=d=>L+(x1===x0?(W-L-R)/2:(d-x0)/(x1-x0)*(W-L-R)),Y=t=>H-B-t/y1*(H-B-T);
  const ns="http://www.w3.org/2000/svg",mk=(n,a,txt)=>{const e=document.createElementNS(ns,n);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e};
  const svg=mk("svg",{viewBox:`0 0 ${W} ${H}`,width:"100%",role:"img","aria-label":label});
  for(let i=0;i<=4;i++){const t=y1*i/4,y=Y(t);svg.append(mk("line",{x1:L,x2:W-R,y1:y,y2:y,stroke:"var(--line)"}),mk("text",{x:L-6,y:y+4,"text-anchor":"end"},fmt(t)))}
  const ds=[...new Set(xs)].sort((a,b)=>a-b),shown=ds.length<=7?ds:[x0,x1];
  shown.forEach(d=>svg.append(mk("text",{x:X(d),y:H-8,"text-anchor":ds.length>7?(d===x0?"start":"end"):"middle"},dlabel(d))));
  series.forEach(s=>{
    const p=[...s.pts].sort((a,b)=>a.x-b.x);
    if(p.length>1)svg.append(mk("polyline",{points:p.map(q=>X(q.x)+","+Y(q.y)).join(" "),fill:"none",stroke:s.color,"stroke-width":2.5,"stroke-linejoin":"round",...(s.dash?{"stroke-dasharray":"6 4"}:{})}));
    p.forEach(q=>{const c=mk("circle",{cx:X(q.x),cy:Y(q.y),r:4,fill:s.color,stroke:"var(--panel)","stroke-width":1.5});c.append(mk("title",{},q.tip));svg.append(c)});
  });
  const lg=el("div",null,"legend");
  series.forEach(s=>{const i=el("span",null,"who"),d=el("span","","dot");d.style.background=s.color;i.append(d,s.name);lg.append(i)});
  host.append(svg,lg);
}

// one rank tile; `ref` is a ranked row or undefined (not played)
function tile(ref,game){
  const t=el("span",null,"tile");
  if(!ref){t.classList.add("none");t.title=game+": not played";t.setAttribute("aria-label",t.title);return t}
  const what=ref.game+" "+fmt(ref.timeSeconds)+(ref.hints?` + ${HINT_PENALTY}s hint`:"");
  if(!ref.rank){t.classList.add("solo");t.textContent=NONE;t.title=what+": played alone";}
  else{t.classList.add("r"+Math.min(ref.rank,3));t.textContent=ref.rank;t.title=what+": "+ord(ref.rank)+" of "+ref.n}
  t.setAttribute("aria-label",t.title);return t;
}
const rankLegend=()=>{
  const l=el("p",null,"key");
  [["r1","1","first"],["r2","2","second"],["r3","3","third or lower"],["solo",NONE,"played alone"],["none","","not played"]].forEach(([c,n,t])=>{
    const w=el("span",null,"key-i"),k=el("span",n,"tile "+c);w.append(k,t);l.append(w)});
  return l;
};

function loadData(){
  return fetch("data.json",{cache:"no-cache"}).then(r=>r.json()).then(j=>({
    updatedAt:j.updatedAt,
    scores:j.scores.filter(r=>PLAYERS.includes(r.player)&&GAMES.includes(r.game)&&r.timeSeconds>0)}));
}
const LOAD_ERR="Could not load data.json. Open the page from a web server (python3 -m http.server), not as a local file.";
