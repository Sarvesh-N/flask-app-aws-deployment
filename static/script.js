document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname === '/dashboard') {
        showSection('events');
    }
});

let currentEvents_data = [];

// --- Auth Functions ---
async function login() {
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;

    try {
        const res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (data.success) {
            window.location.href = '/dashboard';
        } else {
            alert(data.message || 'Login failed');
        }
    } catch (e) { console.error(e); alert('Error logging in'); }
}

async function register() {
    const u = document.getElementById('reg-username').value;
    const p = document.getElementById('reg-password').value;
    const r = document.getElementById('reg-role').value;

    try {
        const res = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p, role: r })
        });
        const data = await res.json();
        if (data.success) {
            alert('Registration successful! Please login.');
            showTab('login');
        } else {
            alert(data.message || 'Registration failed');
        }
    } catch (e) { console.error(e); alert('Error registering'); }
}

function showTab(tabId) {
    document.getElementById('login-form').style.display = tabId === 'login' ? 'block' : 'none';
    document.getElementById('register-form').style.display = tabId === 'register' ? 'block' : 'none';

    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const btns = document.querySelectorAll('.tab-btn');
    btns.forEach(btn => {
        if (btn.innerText.toLowerCase().includes(tabId)) {
            btn.classList.add('active');
        }
    });
}

// --- Dashboard Functions ---
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.style.display = 'none');

    document.querySelectorAll('.sidebar li').forEach(l => l.classList.remove('active'));

    const section = document.getElementById(sectionId + '-section');
    if (section) {
        section.classList.add('active');
        section.style.display = 'block';
    }

    if (sectionId === 'events') loadEvents();
    if (sectionId === 'my-registrations') loadRegistrations();
}

async function loadEvents() {
    try {
        const res = await fetch('/api/events');
        const events = await res.json();
        currentEvents_data = events;
        const container = document.getElementById('events-list');
        container.innerHTML = '';

        events.forEach(ev => {
            const card = document.createElement('div');
            card.className = 'card';
            const adminBtnStyle = (window.userRole === 'admin') ? 'inline-block' : 'none';

            card.innerHTML = `
                <h3>${ev.title}</h3>
                <p><strong>Date:</strong> ${new Date(ev.date).toLocaleString()}</p>
                <p><strong>Location:</strong> ${ev.location}</p>
                <p>${ev.description}</p>
                <div class="card-actions">
                    <button class="btn-sm btn-register" onclick="registerForEvent(${ev.id})">Register</button>
                    <button class="btn-sm" onclick="openEditModal(${ev.id})" style="display: ${adminBtnStyle}; background: #f59e0b;">Edit</button>
                    <button class="btn-sm btn-delete" onclick="deleteEvent(${ev.id})" style="display: ${adminBtnStyle};">Delete</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) { console.error(e); }
}

async function loadRegistrations() {
    try {
        const res = await fetch('/api/registrations');
        const regs = await res.json();
        const container = document.getElementById('registrations-list');

        if (!container) return;

        container.innerHTML = '';
        if (regs.length === 0) {
            container.innerHTML = '<p>No registrations found.</p>';
            return;
        }

        regs.forEach(reg => {
            const item = document.createElement('div');
            item.className = 'card';
            const title = reg.title || 'Unknown Event';
            const user = reg.username ? `User: ${reg.username}` : '';

            item.innerHTML = `
                <h3>${title}</h3>
                ${user ? `<p>${user}</p>` : ''}
                <p>Registered</p>
            `;
            container.appendChild(item);
        });
    } catch (e) { console.error(e); }
}

async function registerForEvent(eventId) {
    try {
        const res = await fetch('/api/registrations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_id: eventId })
        });
        const data = await res.json();
        alert(data.message);
    } catch (e) { alert('Error registering'); }
}

async function deleteEvent(eventId) {
    if (!confirm('Are you sure you want to delete this event?')) return;
    try {
        const res = await fetch(`/api/events/${eventId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            loadEvents();
            alert('Event deleted');
        } else {
            alert(data.message);
        }
    } catch (e) { alert('Error deleting event'); }
}

// Global modal functions
function openModal(id) { document.getElementById(id).style.display = 'flex'; }
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

function openCreateModal() {
    document.getElementById('modal-title').innerText = 'Create Event';
    document.getElementById('evt-id').value = '';
    document.getElementById('evt-title').value = '';
    document.getElementById('evt-desc').value = '';
    document.getElementById('evt-date').value = '';
    document.getElementById('evt-loc').value = '';
    openModal('create-event-modal');
}

function openEditModal(id) {
    const ev = currentEvents_data.find(e => e.id === id);
    if (!ev) return;
    document.getElementById('modal-title').innerText = 'Edit Event';
    document.getElementById('evt-id').value = ev.id;
    document.getElementById('evt-title').value = ev.title;
    document.getElementById('evt-desc').value = ev.description;

    const d = new Date(ev.date);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    document.getElementById('evt-date').value = d.toISOString().slice(0, 16);

    document.getElementById('evt-loc').value = ev.location;
    openModal('create-event-modal');
}

async function handleEventSubmit() {
    const id = document.getElementById('evt-id').value;
    const title = document.getElementById('evt-title').value;
    const desc = document.getElementById('evt-desc').value;
    const date = document.getElementById('evt-date').value;
    const loc = document.getElementById('evt-loc').value;

    const isEdit = !!id;
    const url = isEdit ? `/api/events/${id}` : '/api/events';
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, description: desc, date: date, location: loc })
        });

        const data = await res.json();
        if (data.success) {
            closeModal('create-event-modal');
            loadEvents();
            alert(isEdit ? 'Event updated!' : 'Event created!');
        } else {
            alert(data.message);
        }
    } catch (e) { alert('Error saving event'); }
}

// --- Agent Chat ---
async function sendCommand() {
    const input = document.getElementById('agent-input');
    const command = input.value;
    if (!command.trim()) return;

    addMessage(command, 'user');
    input.value = '';

    try {
        const res = await fetch('/api/agent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command })
        });
        const data = await res.json();
        addMessage(data.response, 'ai');
    } catch (e) {
        addMessage("Sorry, I encountered an error handling that command.", 'ai');
    }
}

function addMessage(text, type) {
    const history = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = `message ${type}`;
    msg.innerHTML = text.replace(/\n/g, '<br>');
    history.appendChild(msg);
    history.scrollTop = history.scrollHeight;
}

function togglePwd(id, el) {
    const input = document.getElementById(id);
    input.type = input.type === "password" ? "text" : "password";
}
