const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');
const send = document.getElementById('send');
let sid = localStorage.getItem('sid') || '';

const fmt = n => Number(n).toLocaleString('en-US') + ' د.ع';

function addMsg(text, who) {
  const d = document.createElement('div');
  d.className = 'msg ' + who;
  d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

function addTyping() {
  const d = document.createElement('div');
  d.className = 'typing';
  d.id = 'typing';
  d.textContent = 'اكتب الوكيل…';
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}
function removeTyping() { document.getElementById('typing')?.remove(); }

function addCard(card) {
  const d = document.createElement('div');
  d.className = 'card';
  const props = card.proposals.map(p => `
    <div class="proposal">
      <div class="p-row"><span class="p-main">${p.to}</span><span class="p-amount">${fmt(p.amount)}</span></div>
      <div class="p-row"><span class="label">${p.type} — ${p.detail}</span></div>
    </div>`).join('');
  d.innerHTML = `
    <div class="head">⚠️ تأكيد مطلوب — شيء ما يننفذ بدون موافقتك</div>
    <div class="body">${props}</div>
    <div class="foot">
      <span>الرصيد: ${fmt(card.balance_before)} ← <b style="color:var(--accent)">${fmt(card.balance_after)}</b></span>
    </div>
    <div class="btns">
      <button class="btn ok" data-ans="نعم">نعم، نفّذ</button>
      <button class="btn no" data-ans="لا">لا، إلغاء</button>
    </div>`;
  d.querySelectorAll('[data-ans]').forEach(b =>
    b.addEventListener('click', () => send2(b.dataset.ans)));
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

function addChoices(choices) {
  const d = document.createElement('div');
  d.className = 'choices';
  choices.forEach((c, i) => {
    const b = document.createElement('button');
    b.className = 'choice';
    b.textContent = (i + 1) + '. ' + c;
    b.addEventListener('click', () => send2(String(i + 1)));
    d.appendChild(b);
  });
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

async function send2(text) {
  addMsg(text, 'user');
  send.disabled = true;
  addTyping();
  try {
    const r = await fetch(`/api/chat?sid=${encodeURIComponent(sid)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await r.json();
    sid = data.sid;
    localStorage.setItem('sid', sid);
    removeTyping();
    (data.messages || []).forEach(m => addMsg(m, 'bot'));
    (data.cards || []).forEach(addCard);
    if (data.choices) addChoices(data.choices);
    await loadMe();
  } catch (e) {
    removeTyping();
    addMsg('صار خطأ بالاتصال. حاول مرة ثانية.', 'bot');
  }
  send.disabled = false;
  input.focus();
}

/* ---- voice input (stretch): record, upload, then same reply rendering ---- */
const mic = document.getElementById('mic');
let recording = false, mediaRec = null, chunks = [];

mic.addEventListener('click', async () => {
  if (recording) { mediaRec?.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRec = new MediaRecorder(stream);
    chunks = [];
    mediaRec.ondataavailable = e => chunks.push(e.data);
    mediaRec.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      mic.classList.remove('rec');
      recording = false;
      const blob = new Blob(chunks, { type: 'webm' });
      const fd = new FormData();
      fd.append('file', blob, 'voice.webm');
      addTyping();
      send.disabled = true;
      try {
        const r = await fetch(`/api/voice?sid=${encodeURIComponent(sid)}`, { method: 'POST', body: fd });
        const data = await r.json();
        sid = data.sid || sid;
        localStorage.setItem('sid', sid);
        removeTyping();
        if (data.transcript) addMsg('🎙 ' + data.transcript, 'user');
        (data.messages || []).forEach(m => addMsg(m, 'bot'));
        (data.cards || []).forEach(addCard);
        if (data.choices) addChoices(data.choices);
        await loadMe();
      } catch (e) {
        removeTyping();
        addMsg('صار خطأ بتسجيل الصوت. حاول مرة ثانية.', 'bot');
      }
      send.disabled = false;
    };
    mediaRec.start();
    recording = true;
    mic.classList.add('rec');
  } catch (e) {
    addMsg('ما أكدر أوصل للمايك. تأكد من الصلاحيات.', 'bot');
  }
});

async function loadMe() {
  const r = await fetch('/api/me');
  const data = await r.json();
  document.getElementById('userbox').style.display = 'flex';
  document.getElementById('username').textContent = data.user.name;
  document.getElementById('balance').textContent = fmt(data.user.balance_iqd);
}

form.addEventListener('submit', e => {
  e.preventDefault();
  const t = input.value.trim();
  if (!t) return;
  input.value = '';
  send2(t);
});

document.getElementById('resetBtn').addEventListener('click', async () => {
  await fetch(`/api/reset?sid=${encodeURIComponent(sid)}`, { method: 'POST' });
  sid = '';
  localStorage.removeItem('sid');
  chat.innerHTML = '';
  addMsg('هلا! گلي شنو تريد: «دفع فاتورة الكهرباء»، «حول 50 الف لأحمد»، «كم رصيدي»…', 'bot');
  await loadMe();
});

document.querySelectorAll('.quick button').forEach(b =>
  b.addEventListener('click', () => send2(b.dataset.t)));

loadMe().then(() =>
  addMsg('هلا! گلي شنو تريد: «دفع فاتورة الكهرباء»، «حول 50 الف لأحمد»، «كم رصيدي»…', 'bot'));
