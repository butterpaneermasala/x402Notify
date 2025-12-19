const BASE = location.origin.replace(/:\d+$/, ':8001');
const priceEl = document.getElementById('price');
const countEl = document.getElementById('count');
const chatEl = document.getElementById('chat');
const subBtn = document.getElementById('sub');
const unsubBtn = document.getElementById('unsub');
const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');

async function api(path, method='GET', body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {'Content-Type':'application/json'},
    body: body ? JSON.stringify(body) : undefined
  });
  return res.json();
}

subBtn.onclick = async () => {
  const chat = chatEl.value.trim();
  if (!chat) return alert('enter chat id');
  await api('/subscribe','POST',{chat_id:chat});
  poll();
}
unsubBtn.onclick = async () => {
  const chat = chatEl.value.trim();
  if (!chat) return alert('enter chat id');
  await api('/unsubscribe','POST',{chat_id:chat});
  poll();
}

let history = [];
function draw(price){
  history.push(price);
  if (history.length>60) history.shift();
  const w = canvas.width, h = canvas.height;
  ctx.fillStyle='#071024'; ctx.fillRect(0,0,w,h);
  ctx.strokeStyle='#22c55e'; ctx.lineWidth=2; ctx.beginPath();
  history.forEach((p,i)=>{
    const x = (i/(history.length-1||1))*w;
    const y = h - ((p-2500)/(2000))*h;
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  }); ctx.stroke();
}

async function poll(){
  try{
    const s = await api('/status');
    priceEl.textContent = `$${s.price}`;
    countEl.textContent = s.subscribers.length;
    draw(s.price);
  }catch(e){ console.warn(e); }
}

setInterval(poll,5000);
poll();
