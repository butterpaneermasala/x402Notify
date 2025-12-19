const BASE = location.origin.replace(/:\d+$/, ':8001');
const priceEl = document.getElementById('price');
const countEl = document.getElementById('count');
const lastPriceEl = document.getElementById('last-price');
const chatEl = document.getElementById('chat');
const toggleBtn = document.getElementById('toggle');
const statusMsg = document.getElementById('status-msg');
const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');

// visual settings
const HISTORY_LEN = 400;
const POLL_MS = 150; // poll backend every 150ms

let history = [];
let lastFetchAt = 0;
let lastFetchedPrice = null;
let displayedPrice = null; // smoothed price used for drawing
let devicePixelRatio = Math.max(1, window.devicePixelRatio || 1);

function resize() {
  // handle high-DPI screens
  const w = canvas.clientWidth;
  const h = parseInt(canvas.style.height || canvas.clientHeight || 320, 10);
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  canvas.width = Math.floor(w * devicePixelRatio);
  canvas.height = Math.floor(h * devicePixelRatio);
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}
window.addEventListener('resize', resize);
resize();

async function api(path, method = 'GET', body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

// Toggle subscribe/unsubscribe with single button
async function isSubscribed(chat) {
  try {
    const s = await api('/status');
    return Array.isArray(s.subscribers) && s.subscribers.includes(chat);
  } catch (e) {
    return false;
  }
}

toggleBtn.onclick = async () => {
  const chat = chatEl.value.trim();
  if (!chat) return alert('enter chat id');
  toggleBtn.disabled = true;
  try {
    const currently = await isSubscribed(chat);
    if (currently) {
      await api('/unsubscribe', 'POST', { chat_id: chat });
      statusMsg.textContent = 'Not subscribed';
      toggleBtn.textContent = 'Subscribe';
    } else {
      await api('/subscribe', 'POST', { chat_id: chat });
      statusMsg.textContent = 'Subscribed';
      toggleBtn.textContent = 'Unsubscribe';
    }
  } catch (e) {
    console.warn(e);
    alert('Request failed');
  } finally {
    toggleBtn.disabled = false;
  }
};

function pushPrice(p) {
  history.push(p);
  if (history.length > HISTORY_LEN) history.shift();
}

function drawGrid(w, h) {
  ctx.clearRect(0, 0, w, h);
  // background
  ctx.fillStyle = '#071024';
  ctx.fillRect(0, 0, w, h);

  // subtle horizontal grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  const rows = 4;
  for (let i = 0; i <= rows; i++) {
    const y = (i / rows) * h;
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
    ctx.stroke();
  }

  // faint vertical grid
  ctx.strokeStyle = 'rgba(255,255,255,0.02)';
  const cols = 8;
  for (let j = 0; j <= cols; j++) {
    const x = (j / cols) * w;
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
    ctx.stroke();
  }
}

function drawLine() {
  const w = canvas.width / devicePixelRatio, h = canvas.height / devicePixelRatio;
  if (history.length < 2) return;
  const maxP = Math.max(...history);
  const minP = Math.min(...history);
  const range = Math.max(1, maxP - minP);

  // build path
  const path = new Path2D();
  history.forEach((p, i) => {
    const x = (i / (history.length - 1 || 1)) * w;
    const y = h - ((p - minP) / range) * h;
    if (i === 0) path.moveTo(x, y);
    else path.lineTo(x, y);
  });

  // fill under curve
  const fillPath = new Path2D(path);
  fillPath.lineTo(w, h);
  fillPath.lineTo(0, h);
  fillPath.closePath();
  const gFill = ctx.createLinearGradient(0, 0, 0, h);
  gFill.addColorStop(0, 'rgba(34,197,94,0.12)');
  gFill.addColorStop(1, 'rgba(34,197,94,0.02)');
  ctx.fillStyle = gFill;
  ctx.fill(fillPath);

  // stroke
  ctx.lineWidth = 2.5;
  const grad = ctx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, '#ef4444');
  grad.addColorStop(1, '#22c55e');
  ctx.strokeStyle = grad;
  ctx.stroke(path);

  // last price marker and label
  const lp = history[history.length - 1];
  const prev = history[history.length - 2] || lp;
  const lx = w - 16;
  const ly = h - ((lp - minP) / range) * h;
  const color = lp >= prev ? '#22c55e' : '#ef4444';
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(lx, ly, 6, 0, Math.PI * 2);
  ctx.fill();

  // price label box
  const label = `$${lp}`;
  ctx.font = '14px Inter, system-ui';
  ctx.textAlign = 'right';
  ctx.fillStyle = 'rgba(255,255,255,0.95)';
  ctx.fillText(label, lx - 12, ly - 12);
}

function render() {
  const w = canvas.width, h = canvas.height;
  drawGrid(w, h);
  drawLine();
}

// animation loop for smoothing
function animate() {
  // interpolate displayedPrice toward lastFetchedPrice
  if (lastFetchedPrice != null) {
    if (displayedPrice == null) displayedPrice = lastFetchedPrice;
    // smoother exponential smoothing
    displayedPrice += (lastFetchedPrice - displayedPrice) * 0.12;
    // push interpolated value into history (but limit frequency)
    const now = Date.now();
    if (now - lastFetchAt >= POLL_MS / 2) {
      pushPrice(Math.round(displayedPrice));
      lastFetchAt = now;
    }
  }
  // update UI text
  if (history.length) {
    const lp = history[history.length - 1];
    priceEl.textContent = `$${lp}`;
    if (lastPriceEl) lastPriceEl.textContent = `$${lp}`;
  }
  // subscriber count is managed from pollLoop
  // render with correct pixel dims
  render();
  requestAnimationFrame(animate);
}

async function pollLoop() {
  while (true) {
    try {
      const s = await api('/status');
      lastFetchedPrice = s.price;
      // update subscriber count separately
      if (Array.isArray(s.subscribers)) countEl.textContent = s.subscribers.length;
    } catch (e) {
      console.warn('poll error', e);
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}

// start
window.addEventListener('load', () => {
  devicePixelRatio = Math.max(1, window.devicePixelRatio || 1);
  resize();
  animate();
  pollLoop();
});

window.addEventListener('resize', () => {
  // debounce resize
  clearTimeout(window._resizeTO);
  window._resizeTO = setTimeout(resize, 80);
});
