// Simple static demo: mock ETH price feed with subscribe/unsubscribe
const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');
const width = canvas.width; const height = canvas.height;

const events = document.getElementById('events');
const subState = document.getElementById('subState');
const toggleBtn = document.getElementById('toggleSub');
const unsubBtn = document.getElementById('unsubscribe');
const chatIdInput = document.getElementById('chatId');

let subscribed = false;
const SUB_KEY = 'demo_subscribed_v1';

function loadState(){
  try{const s = localStorage.getItem(SUB_KEY); if(s){const o=JSON.parse(s); subscribed=!!o.sub; chatIdInput.value=o.id||''}}catch(e){/*ignore*/}
  updateUI();
}
function saveState(){ localStorage.setItem(SUB_KEY, JSON.stringify({sub:subscribed, id:chatIdInput.value||''})); updateUI(); }
function updateUI(){ subState.textContent = subscribed ? 'yes' : 'no'; toggleBtn.textContent = subscribed ? 'Subscribed' : 'Subscribe'; }

toggleBtn.addEventListener('click', ()=>{ subscribed = true; saveState(); addEvent('You subscribed') });
unsubBtn.addEventListener('click', ()=>{ subscribed = false; saveState(); addEvent('You unsubscribed') });

function addEvent(txt){ const li=document.createElement('li'); li.textContent = `[${new Date().toLocaleTimeString()}] ${txt}`; events.prepend(li); }

// Price simulation
const history = [];
let elapsed = 0; // seconds
let baseTarget = 3500; // toggles each minute to 4000 or 3000

function step(){
  elapsed++;
  // Each minute toggle target: odd minutes -> 4000 (cross), even minutes -> 3000 (drop)
  const minute = Math.floor(elapsed/60);
  const phase = minute % 2 === 0 ? 'up' : 'down';
  baseTarget = phase === 'up' ? 4000 : 3000;

  // create price that moves toward baseTarget with small noise
  const last = history.length ? history[history.length-1] : 3500;
  // move fractionally towards target
  let price = last + (baseTarget - last) * 0.06 + (Math.random()-0.5)*30;
  price = Math.max(2000, Math.min(5000, Math.round(price)));

  history.push(price); if(history.length>120) history.shift();

  // detect crossing events: when price crosses above 4000 or below 3000
  if(price >= 4000 && (!history[history.length-2] || history[history.length-2] < 4000)){
    addEvent('Price crossed ≥ 4000'); if(subscribed) addEvent('✅ Delivered to subscribers (simulated)');
  }
  if(price <= 3000 && (!history[history.length-2] || history[history.length-2] > 3000)){
    addEvent('Price dropped ≤ 3000'); if(subscribed) addEvent('✅ Delivered to subscribers (simulated)');
  }

  draw();
}

function draw(){
  ctx.clearRect(0,0,width,height);
  // background
  ctx.fillStyle = '#071024'; ctx.fillRect(0,0,width,height);

  // draw bands
  const minP = 2000, maxP = 5000; const range = maxP-minP;
  function yFor(p){ return height - 20 - ((p-minP)/range)*(height-40); }
  const lowY = yFor(3000); const highY = yFor(4000);

  ctx.fillStyle='rgba(239,68,68,0.06)'; ctx.fillRect(40, lowY, width-80, height-20-lowY);
  ctx.fillStyle='rgba(34,197,94,0.06)'; ctx.fillRect(40, 20, width-80, highY-20);

  // axis labels
  ctx.fillStyle='#9ca3af'; ctx.font='12px Inter'; ctx.fillText('$5000', 10, 28);
  ctx.fillText('$4000', 10, highY+4); ctx.fillText('$3000',10, lowY+4); ctx.fillText('$2000',10, height-6);

  // draw line
  ctx.beginPath(); ctx.lineWidth=2; ctx.strokeStyle='#fff';
  history.forEach((p,i)=>{
    const x = 40 + (i/(Math.max(1,history.length-1)))*(width-80);
    const y = yFor(p);
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
}

// tick every 1s
loadState();
setInterval(step, 1000);
// initialize with 60s worth of simulated data
for(let i=0;i<60;i++){ step(); }
