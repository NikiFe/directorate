let userId = localStorage.getItem('userId') || '';
const userInput = document.getElementById('userId');
const setUserBtn = document.getElementById('set-user');
const walletDiv = document.getElementById('wallet');
const ledgerBody = document.getElementById('ledger-body');
const ticketForm = document.getElementById('ticket-form');
const notifList = document.getElementById('notif-list');
const ticketResult = document.getElementById('ticket-result');

if (userId) {
  userInput.value = userId;
  loadWallet();
  loadLedger();
  loadNotifications();
  initWS();
}

setUserBtn.addEventListener('click', () => {
  userId = userInput.value.trim();
  localStorage.setItem('userId', userId);
  loadWallet();
  loadLedger();
  loadNotifications();
  initWS();
});

function loadWallet() {
  fetch(`/users/${userId}`)
    .then(r => r.json())
    .then(u => {
      walletDiv.textContent = `${u.rank} \u25B2  Credits: ${u.credits}  Balance: ${u.balance}`;
    });
}

function loadLedger() {
  fetch(`/transactions?user_id=${userId}`)
    .then(r => r.json())
    .then(data => {
      ledgerBody.innerHTML = '';
      data.forEach(tx => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${new Date(tx.ts).toLocaleString()}</td><td>${tx.type}</td><td>${tx.amount_cr}</td><td>${tx.amount_pay}</td>`;
        ledgerBody.appendChild(tr);
      });
    });
}

function loadNotifications() {
  fetch(`/notifications?user_id=${userId}`)
    .then(r => r.json())
    .then(list => {
      notifList.innerHTML = '';
      list.forEach(n => {
        const li = document.createElement('li');
        li.textContent = `${new Date(n.ts).toLocaleString()} - ${n.message}`;
        notifList.appendChild(li);
      });
    });
}

function initWS() {
  if (!userId) return;
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  ws.onmessage = evt => {
    const msg = JSON.parse(evt.data);
    if (msg.payload.user_id === userId) {
      if (msg.event === 'credits_update' || msg.event === 'reward_granted') {
        loadWallet();
        loadLedger();
      }
      if (msg.event === 'notify') {
        loadNotifications();
      }
    }
  };
}

ticketForm.addEventListener('submit', e => {
  e.preventDefault();
  const form = e.target;
  const payload = {
    title: form.title.value,
    body_md: form.body.value,
    category: form.category.value,
    sub_category: form.subcategory.value,
    author_id: userId,
    assignee_id: userId,
    target_rank: 'marshal'
  };
  fetch('/tickets', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
    .then(r => r.json())
    .then(t => {
      const sub = {
        reward_credits: parseInt(form.reward_credits.value || '0'),
        reward_pay: parseFloat(form.reward_pay.value || '0')
      };
      fetch(`/tickets/${t._id}/submit`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify(sub)})
        .then(() => {
          form.reset();
          ticketResult.textContent = 'Ticket submitted.';
          setTimeout(() => ticketResult.textContent = '', 3000);
        });
    });
});

// simple page navigation
const navButtons = document.querySelectorAll('nav button');
navButtons.forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  document.getElementById(btn.dataset.page).style.display = 'block';
}));
