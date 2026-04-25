/**
 * Engram Intelligence Portal - Nebula Vortex V3
 * High-Fidelity Particle Engine (Engram Blue Edition)
 */
class NebulaVortex {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.W = 0; this.H = 0; this.cx = 0; this.cy = 0;
        this.mouse = { x: -1, y: -1 };
        this.time = 0;
        this.NUM = 1800;
        this.particles = [];
        this.sparks = [];
        
        this.init();
        this.animate();
        
        window.addEventListener('resize', () => this.resize());
        window.addEventListener('mousemove', (e) => {
            const r = this.canvas.getBoundingClientRect();
            this.mouse.x = (e.clientX - r.left) * devicePixelRatio;
            this.mouse.y = (e.clientY - r.top) * devicePixelRatio;
        });
        window.addEventListener('mouseleave', () => { this.mouse.x = -1; this.mouse.y = -1; });
    }

    init() {
        this.updateSize();
        this.particles = [];
        this.bgParticles = [];
        this.NUM = 1400; // Optimized for performance and density
        const cx = this.cx;
        const cy = this.cy;
        
        // Engram Electric Blue Palette - Toned down whites
        const palette = [
            [41, 171, 226],  // Brand Blue
            [0, 114, 187],   // Deep Blue
            [131, 209, 247], // Light Blue
            [20, 80, 120],   // Shadow Blue
            [41, 171, 226],  // Brand Blue Duplicate
            [180, 230, 255], // Ultra-soft Blue (instead of pure white)
            [0, 114, 187]    // Deep Blue Duplicate
        ];

        // Background Starfield (Fixed Particles)
        for (let i = 0; i < 1000; i++) {
            this.bgParticles.push({
                x: Math.random() * this.W,
                y: Math.random() * this.H,
                size: Math.random() * 0.7 + 0.1,
                alpha: Math.random() * 0.3 + 0.1,
                col: palette[Math.floor(Math.random() * palette.length)]
            });
        }

        for (let i = 0; i < this.NUM; i++) {
            const angle = Math.random() * Math.PI * 2;
            const orbitOffset = Math.random() * Math.PI * 2;
            const r = Math.pow(Math.random(), 0.5) * 260 * devicePixelRatio;
            const col = palette[Math.floor(Math.random() * palette.length)];
            
            // Calculate initial amoeba wobble at birth (time = 0)
            const initialWobble = 1 + Math.sin(angle * 4) * 0.15 * (r / (260 * devicePixelRatio));

            this.particles.push({
                baseAngle: angle,
                baseR: r,
                orbitOffset,
                x: cx + Math.cos(angle + orbitOffset) * (r * initialWobble),
                y: cy + Math.sin(angle + orbitOffset) * (r * initialWobble),
                vx: 0, vy: 0,
                size: (Math.random() * 1.2 + 0.2) * devicePixelRatio,
                col,
                alpha: Math.random() * 0.55 + 0.25,
                speed: Math.random() * 0.003 + 0.0008,
                drag: 0.82 + Math.random() * 0.08, // Increased drag to eliminate spring bounce
            });
        }
    }

    updateSize() {
        this.W = this.canvas.width = window.innerWidth * devicePixelRatio;
        this.H = this.canvas.height = window.innerHeight * devicePixelRatio;
        this.cx = this.W / 2;
        this.cy = this.H / 2;
    }

    resize() {
        this.updateSize();
        this.init(); // Re-init particles on resize
    }

    spawnSpark(mx, my) {
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 0.8 + 0.2;
        this.sparks.push({
            x: mx + (Math.random() - 0.5) * 20,
            y: my + (Math.random() - 0.5) * 20,
            vx: Math.cos(angle) * speed * 2,
            vy: Math.sin(angle) * speed * 2,
            size: (Math.random() * 0.7 + 0.2) * devicePixelRatio,
            alpha: Math.random() * 0.4 + 0.2,
            life: 1.0,
            decay: Math.random() * 0.018 + 0.010,
        });
    }

    animate() {
        this.time += 0.010;
        this.ctx.clearRect(0, 0, this.W, this.H);

        // Instant Core Size (No Intro)
        const breath = 1 + 0.01 * Math.sin(this.time * 0.3);
        
        // Background Starfield Render
        this.bgParticles.forEach(p => {
            const [r, g, b] = p.col;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${r},${g},${b},${p.alpha})`;
            this.ctx.fill();
        });

        const glowRadius = Math.min(this.W, this.H) * 0.25;
        const glow = this.ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, glowRadius);
        glow.addColorStop(0, 'rgba(41, 171, 226, 0.1)');
        glow.addColorStop(0.5, 'rgba(41, 171, 226, 0.05)');
        glow.addColorStop(1, 'rgba(0,0,0,0)');
        this.ctx.fillStyle = glow;
        this.ctx.fillRect(0, 0, this.W, this.H);

        const hasMouse = this.mouse.x > 0;
        if (hasMouse && Math.random() < 0.35) {
            this.spawnSpark(this.mouse.x, this.mouse.y);
        }

        for (let i = 0; i < this.NUM; i++) {
            const p = this.particles[i];
            const orbit = this.time * p.speed * 60 + p.orbitOffset;
            
            // 4 lobes that undulate over time, more subtle for a grounded feel
            const amoebaWobble = 1 + Math.sin(p.baseAngle * 4 - this.time * 2) * 0.08 * (p.baseR / (260 * devicePixelRatio));
            
            const targetX = this.cx + Math.cos(p.baseAngle + orbit) * (p.baseR * breath * amoebaWobble);
            const targetY = this.cy + Math.sin(p.baseAngle + orbit) * (p.baseR * breath * amoebaWobble);

            let fx = (targetX - p.x) * 0.02; // Reduced force for smoother target acquisition
            let fy = (targetY - p.y) * 0.02;

            if (hasMouse) {
                const dx = p.x - this.mouse.x;
                const dy = p.y - this.mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const influence = Math.min(this.W, this.H) * 0.10;
                if (dist < influence && dist > 0.5) {
                    const strength = (1 - dist / influence) * 1.5;
                    fx += (dx / dist) * strength;
                    fy += (dy / dist) * strength;
                }
            }

            p.vx = (p.vx + fx) * p.drag;
            p.vy = (p.vy + fy) * p.drag;
            p.x += p.vx;
            p.y += p.vy;

            const dimCenter = Math.min(1, Math.hypot(p.x - this.cx, p.y - this.cy) / (Math.min(this.W, this.H) * 0.08));
            const [r, g, b] = p.col;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${r},${g},${b},${(p.alpha * dimCenter).toFixed(2)})`;
            this.ctx.fill();
        }

        for (let i = this.sparks.length - 1; i >= 0; i--) {
            const s = this.sparks[i];
            s.x += s.vx; s.y += s.vy;
            s.vx *= 0.97; s.vy *= 0.97;
            s.life -= s.decay;
            if (s.life <= 0) { this.sparks.splice(i, 1); continue; }
            this.ctx.beginPath();
            this.ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(41, 171, 226, ${(s.alpha * s.life).toFixed(2)})`;
            this.ctx.fill();
        }

        requestAnimationFrame(() => this.animate());
    }
}

// Global Intelligence State
// Dynamic API Base: Auto-detects hostname and bridges the Docker port gap
const HOST = window.location.hostname;
const API_BASE = window.location.origin.includes(':5173') 
    ? `http://${HOST}:8000/api/v1` 
    : '/api/v1';

console.log(`Engram: Initializing Intelligence Link at ${API_BASE}`);

let authToken = localStorage.getItem('access_token');
let refreshToken = localStorage.getItem('refresh_token');
let currentUser = null;
let activeDoc = null;
let authMode = 'login'; // login or signup

function isAuth() { return !!authToken; }

// Launch Engine & Heartbeat
window.addEventListener('load', async () => {
    // 1. Start Particle Engine (Unified Experience)
    if (document.getElementById('nebula-canvas')) {
        new NebulaVortex('nebula-canvas');
    }

    // 2. Network Heartbeat Check
    try {
        const res = await fetch(`${API_BASE.replace('/api/v1', '')}/healthy`);
        if (res.ok) {
            console.log("Engram: Backend Link Established ✅");
            if (authToken) { 
                document.body.classList.add('dashboard-mode'); 
                checkAuth(); 
            }
        } else {
            console.error("Engram: Backend is online but rejected the handshake ❌");
        }
    } catch (err) {
        console.error("Engram: Failed to reach Intelligence Backend. Check Docker logs ❌");
    }

    // 3. Cinematic Hero Sequence (Unauthenticated)
    if (!authToken && !sessionStorage.getItem('landingTyped')) {
        await typeWriter(userGreeting, "Welcome to Engram");
        // heroTitle remains static for stability
        heroTitle.innerHTML = "Your Intelligence<br>Workspace";
        sessionStorage.setItem('landingTyped', 'true');
    }
});

// UI Elements
const dropZone = document.getElementById('drop-zone');
const uploadTrigger = document.getElementById('upload-trigger');
const fileInput = document.getElementById('file-input');
const loginBtn = document.getElementById('login-btn');
const signupBtn = document.getElementById('signup-btn');
const logoutBtn = document.getElementById('logout-btn');
const profileBtn = document.getElementById('profile-btn');
const userHub = document.getElementById('user-hub');
const userAvatarBtn = document.getElementById('user-avatar-btn');
const userDropdown = document.getElementById('user-dropdown');
const searchSection = document.getElementById('search-section');
const userGreeting = document.getElementById('user-greeting');
const heroTitle = document.getElementById('hero-title');

// --- HIGH-FIDELITY TYPEWRITER ENGINE ---
async function typeWriter(el, text, speed = 75) {
    if (!el) return;
    el.innerHTML = '';
    let currentText = '';
    const parts = text.split(/(<br>)/); // Preserve line breaks
    
    for (let part of parts) {
        if (part === '<br>') {
            currentText += '<br>';
            el.innerHTML = currentText;
        } else {
            for (let char of part) {
                currentText += char;
                el.innerHTML = currentText;
                await new Promise(r => setTimeout(r, speed));
            }
        }
    }
}

// Toggle Dropdown
userAvatarBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    userDropdown.classList.toggle('hidden');
});

// Prevent dropdown from closing when clicking inside it
userDropdown?.addEventListener('click', (e) => e.stopPropagation());

document.addEventListener('click', () => userDropdown?.classList.add('hidden'));

// Workspace Elements
const workspaceSection = document.getElementById('workspace-section');
const docGrid = document.getElementById('document-grid');
const docCountText = document.getElementById('doc-count');
const loadingOverlay = document.getElementById('loading-overlay');
const loaderText = document.getElementById('loader-text');

// Chat Hub Elements
const chatHub = document.getElementById('chat-hub');
const chatDocName = document.getElementById('chat-doc-name');
const chatMessages = document.getElementById('chat-messages');
const chatHubBody = document.getElementById('chat-hub-body');
const queryInput = document.getElementById('query-input');
const sendQueryBtn = document.getElementById('send-query');
const closeChatBtn = document.getElementById('close-chat');

// Modal Elements
const authModal = document.getElementById('auth-modal');
const authSubmit = document.getElementById('auth-submit');
const modalTitle = document.getElementById('modal-title');
const nameField = document.getElementById('name-field');
const modalToggle = document.getElementById('modal-toggle');
const modalToggleText = document.getElementById('modal-toggle-text');
const modalClose = document.getElementById('modal-close');
const authError = document.getElementById('auth-error');

// Profile & Security Elements
const profileModal = document.getElementById('profile-modal');
const profileInfo = document.getElementById('profile-info');
const profileClose = document.getElementById('profile-close');
const deleteAccountBtn = document.getElementById('delete-account-btn');
const changePasswordBtn = document.getElementById('change-password-btn');
const currentPasswordInput = document.getElementById('current-password');
const newPasswordInput = document.getElementById('new-password');

// SMART FETCH: Handles automatic token refresh
async function authFetch(url, options = {}) {
    if (authToken) {
        options.headers = { ...options.headers, 'Authorization': `Bearer ${authToken}` };
    }

    let response = await fetch(url, options);

    // If 401 (Expired), try to refresh
    if (response.status === 401 && refreshToken) {
        console.log('Auth: Token expired, refreshing...');
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (refreshRes.ok) {
            const data = await refreshRes.json();
            authToken = data.access_token;
            localStorage.setItem('access_token', authToken);
            options.headers['Authorization'] = `Bearer ${authToken}`;
            response = await fetch(url, options);
        } else {
            logout();
        }
    }
    return response;
}

// Initialize
if (authToken) { checkAuth(); }

async function checkAuth() {
    try {
        const response = await authFetch(`${API_BASE}/auth/me`);
        if (response.ok) {
            currentUser = await response.json();
            updateUIForAuth(currentUser);
            fetchDocuments();
        } else { 
            // Silent fail - stay on landing page
            authToken = null;
            localStorage.removeItem('access_token');
        }
    } catch (err) { 
        console.warn("Engram: Connection to Intelligence Backend failed.");
    }
}

function updateUIForAuth(user) {
    document.body.classList.add('dashboard-mode');
    loginBtn.classList.add('hidden');
    signupBtn.classList.add('hidden');
    userHub.classList.remove('hidden');
    searchSection.classList.remove('hidden');
    workspaceSection.classList.remove('hidden');
    const name = user.full_name || user.email.split('@')[0];
    
    // Typing effect ONLY if this is a fresh login/session start
    if (!sessionStorage.getItem('dashboardTyped')) {
        typeWriter(userGreeting, `Hello, ${name}`, 75);
        sessionStorage.setItem('dashboardTyped', 'true');
    } else {
        userGreeting.textContent = `Hello, ${name}`;
    }

    heroTitle.innerHTML = 'Intelligence<br>Workspace';
    
    // Smooth fade in
    searchSection.style.opacity = '0';
    workspaceSection.style.opacity = '0';
    setTimeout(() => {
        searchSection.style.transition = 'opacity 0.8s ease';
        workspaceSection.style.transition = 'opacity 0.8s ease';
        searchSection.style.opacity = '1';
        workspaceSection.style.opacity = '1';
    }, 50);
}

function logout() { 
    console.log("Engram: Performing Secure Sign-Out");
    
    // 1. Memory Purge
    localStorage.removeItem('access_token'); 
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('landingTyped');
    sessionStorage.removeItem('dashboardTyped');
    
    // 2. Force Clean Refresh (Resets UI, Memory, and Vortex automatically)
    window.location.reload();
}

async function deleteAccount() {
    const confirmed = await showConfirm(
        'Permanently Delete Account?',
        'This will erase your profile and all uploaded intelligence. This action is final.'
    );
    if (!confirmed) return;

    try {
        const res = await authFetch(`${API_BASE}/auth/delete-account`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Account successfully purged.', 'success');
            profileModal.classList.add('hidden');
            logout(); // Smooth transition back to login
        } else {
            showToast('Failed to delete account.', 'error');
        }
    } catch (err) {
        showToast('Connection error.', 'error');
    }
}
deleteAccountBtn.onclick = deleteAccount;

// Library Management
async function fetchDocuments() {
    const res = await authFetch(`${API_BASE}/documents/`);
    if (res.ok) {
        const docs = await res.json();
        renderIntelligenceCards(docs);
    }
}

function renderIntelligenceCards(docs) {
    if (!docs || docs.length === 0) {
        docGrid.innerHTML = '<div class="empty-state">No documents yet. Your intelligence library is waiting.</div>';
        docCountText.textContent = '0 Documents';
        return;
    }

    docCountText.textContent = `${docs.length} Documents`;
    docGrid.innerHTML = docs.map(doc => {
        const isFailed = doc.status === 'FAILED';
        const isProcessing = doc.status === 'PENDING' || doc.status === 'PROCESSING';
        const analysisData = doc.analysis || doc.analysis_results || {};
        
        let summaryText = analysisData.summary || '';
        let statusDisplay = doc.status.replace('_', ' ');
        if (doc.status === 'EXTRACTING_TEXT') statusDisplay = 'Extracting Text...';
        else if (doc.status === 'GENERATING_SUMMARY') statusDisplay = 'Analyzing Intelligence...';
        else if (doc.status === 'GENERATING_EMBEDDINGS') statusDisplay = 'Generating Embeddings...';
        else if (doc.status === 'INDEXING') statusDisplay = 'Indexing Knowledge...';

        if (isFailed) {
            summaryText = `<div class="error-text">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;vertical-align:middle;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                Analysis Failed: ${doc.error_message || 'Unexpected processing error'}
            </div>`;
        } else if (isProcessing) {
            summaryText = `<div class="streaming-summary-container">
                <strong class="summary-label" style="display:block; margin-bottom: 5px; color: var(--accent-color); font-size: 0.9rem; letter-spacing: 0.05em; text-transform: uppercase;">Summary</strong>
                <span class="streaming-text">${summaryText}</span>
                <div class="wobble-dots"><span></span><span></span><span></span></div>
            </div>`;
        } else if (!summaryText) {
            summaryText = '<span class="missing-text">Summary data unavailable.</span>';
        } else {
            const cleaned = summaryText.replace(/^(Here is a|This is a|A concise|Summary:).*?:/i, '').replace(/^SUMMARY\s+/i, '').trim();
            summaryText = `<strong class="summary-label" style="display:block; margin-bottom: 5px; color: var(--accent-color); font-size: 0.9rem; letter-spacing: 0.05em; text-transform: uppercase;">Summary</strong>${cleaned}`;
        }
        
        return `
        <div class="intel-card ${isFailed ? 'failed' : ''}" id="card-${doc.id}">
            <div class="intel-header">
                <div class="intel-title-group">
                    <h4>${doc.file_name}</h4>
                    <div class="intel-meta">
                        <span>${new Date(doc.created_at).toLocaleDateString()}</span>
                        <span class="status-badge ${doc.status.toLowerCase()}">${statusDisplay}</span>
                    </div>
                </div>
                <div class="intel-card-actions">
                    ${!isFailed && !isProcessing ? `
                    <button class="btn-icon" data-tooltip="Chat with AI" onclick="openChatHub('${doc.id}', '${doc.file_name.replace(/'/g, "\\'")}')">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    </button>
                    ` : ''}
                    <button class="btn-icon delete-btn" data-tooltip="Delete" onclick="deleteDocument('${doc.id}')">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            </div>
            <div class="intel-summary">
                ${summaryText}
            </div>
        </div>
    `; }).join('');
}

window.openChatHub = async (docId, docName) => {
    activeDoc = { id: docId, file_name: docName };
    chatDocName.textContent = docName;
    chatHub.classList.remove('hidden');
    
    // 1. Fetch Persistent History from Database
    chatMessages.innerHTML = '<div class="loading-history">Loading conversation...</div>';
    try {
        const res = await authFetch(`${API_BASE}/documents/${docId}/chat`);
        const history = await res.json();
        
        chatMessages.innerHTML = '';
        if (history.length === 0) {
            renderMessage('ai', `I've indexed **${docName}**. How can I help you analyze it?`);
        } else {
            history.forEach(msg => renderMessage(msg.role === 'assistant' ? 'ai' : 'user', msg.content));
        }
    } catch (err) {
        chatMessages.innerHTML = '';
        renderMessage('ai', "I'm ready to help, but I couldn't load our previous conversation.");
    }
    
    chatHubBody.scrollTop = chatHubBody.scrollHeight;
};

function renderMessage(role, text, isThinking = false) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    
    // Get first letter for user avatar
    let avatarChar = 'AI';
    if (role === 'user') {
        const name = currentUser?.full_name || currentUser?.email || 'U';
        avatarChar = name.charAt(0).toUpperCase();
    }

    let contentHtml = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
    if (isThinking) {
        msg.classList.add('generating');
        contentHtml = ''; // Keep content empty while generating initial state
    }
    
    const avatarId = `vortex-${Math.random().toString(36).substr(2, 9)}`;
    msg.innerHTML = `
        <div class="avatar-wrapper">
            <canvas class="vortex-canvas" id="${avatarId}" width="80" height="80"></canvas>
            <div class="avatar">${avatarChar}</div>
        </div>
        <div class="msg-content">${contentHtml}</div>
    `;
    
    if (isThinking) {
        msg.classList.add('generating');
        // Initialize micro-vortex with small delay to ensure DOM is ready
        setTimeout(() => {
            const vortex = new MicroVortex(avatarId);
            msg._vortex = vortex; // Store reference to stop it later
        }, 10);
    }
    
    chatMessages.appendChild(msg);
    chatHubBody.scrollTop = chatHubBody.scrollHeight;
    return msg;
}

function addMessage(role, text) {
    return renderMessage(role, text);
}


// Event Listeners
dropZone.addEventListener('click', () => fileInput.click()); // Full pill clickable
uploadTrigger.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener('change', handleUpload);

// Drag & Drop
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('active'); });
dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('active'); });
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('active');
    if (e.dataTransfer.files.length) { handleUpload({ target: { files: e.dataTransfer.files } }); }
});

sendQueryBtn.addEventListener('click', () => {
    const query = queryInput.value.trim();
    if (query) handleQuery(query);
});

queryInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendQueryBtn.click(); });
closeChatBtn.addEventListener('click', () => chatHub.classList.add('hidden'));

async function handleQuery(query) {
    if (!activeDoc) return;
    renderMessage('user', query); 
    queryInput.value = '';
    
    // 1. Show AI Message with Generating Animation
    const aiMsg = renderMessage('ai', '', true);
    const content = aiMsg.querySelector('.msg-content');
    
    try {
        const response = await authFetch(`${API_BASE}/documents/${activeDoc.id}/stream?query=${encodeURIComponent(query)}`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let fullResponse = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            fullResponse += chunk;
            if (!aiMsg.classList.contains('streaming')) {
                aiMsg.classList.add('streaming');
            }
            content.innerHTML = fullResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
            chatHubBody.scrollTop = chatHubBody.scrollHeight;
        }
        // Stop generating animation when done
        aiMsg.classList.remove('generating');
        if (aiMsg._vortex) aiMsg._vortex.stop();
    } catch (err) { 
        aiMsg.classList.remove('generating');
        if (aiMsg._vortex) aiMsg._vortex.stop();
        content.innerHTML = '<span class="error-text">Connection error. Please try again.</span>';
    }
}

async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);

    try {
        // 1. Show persistent loader
        showLoader(`Uploading & Analyzing ${file.name}...`);
        
        const res = await authFetch(`${API_BASE}/documents/upload`, {
            method: 'POST', 
            body: formData
        });

        const data = await res.json();

        if (res.ok) {
            showToast('Indexing started...', 'success');
            
            // 2. Immediate Refresh: Show the document in the list as 'PROCESSING'
            await fetchDocuments();
            hideLoader();
            
            if (data.task_id) {
                const wsBase = API_BASE.split('/api/v1')[0].replace('http', 'ws');
                const socket = new WebSocket(`${wsBase}/ws/${data.task_id}?token=${authToken}`);
                
                socket.onmessage = (event) => {
                    const update = JSON.parse(event.data);
                    const card = document.getElementById(`card-${data.document_id}`);
                    const badge = card?.querySelector('.status-badge');
                    const summaryArea = card?.querySelector('.streaming-text');
                    const label = card?.querySelector('.summary-label');
                    const cardStatusText = card?.querySelector('.analyzing-text');

                    if (update.status === 'SUMMARY_CHUNK' && summaryArea) {
                        if (label) label.style.display = 'block';
                        if (cardStatusText) cardStatusText.remove(); // Clean up status text when stream starts
                        summaryArea.textContent += update.chunk;
                    } else if (update.status === 'COMPLETED') {
                        showToast(`Analysis Ready: ${file.name}`, 'success');
                        fetchDocuments();
                    } else if (update.status === 'FAILED') {
                        showToast(`Analysis failed: ${file.name}`, 'error');
                        fetchDocuments();
                    } else if (badge && update.status !== 'SUMMARY_CHUNK') {
                        badge.className = `status-badge ${update.status.toLowerCase()}`;
                        
                        let stateText = update.status.replace('_', ' ');
                        if (update.status === 'EXTRACTING_TEXT') stateText = 'Extracting Text...';
                        else if (update.status === 'GENERATING_SUMMARY') stateText = 'Analyzing Intelligence...';
                        else if (update.status === 'GENERATING_EMBEDDINGS') stateText = 'Generating Embeddings...';
                        else if (update.status === 'INDEXING') stateText = 'Indexing Knowledge...';
                        
                        badge.textContent = stateText;
                    }
                };
            }
        } else { 
            hideLoader(); 
            // Show specific error from backend (e.g., 415 Unsupported Type)
            showToast(data.detail || 'Upload failed', 'error'); 
        }
    } catch (err) { 
        hideLoader(); 
        showToast('Connection error', 'error'); 
    }
}


// Helpers
function showToast(m, t = 'success') {
    const c = document.getElementById('toast-container');
    c.innerHTML = ''; // Clear previous toasts to avoid piling
    const toast = document.createElement('div');
    toast.className = `toast ${t}`;
    toast.textContent = m;
    c.appendChild(toast);
    
    // Retract after 3.5 seconds, then remove
    setTimeout(() => { 
        toast.classList.add('retract');
        setTimeout(() => toast.remove(), 500); 
    }, 3500);
}
function showLoader(t) { loaderText.textContent = t; loadingOverlay.classList.remove('hidden'); }
function hideLoader() { loadingOverlay.classList.add('hidden'); }

// Custom Confirmation Modal Helper
function showConfirm(title, text) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const textEl = document.getElementById('confirm-text');
        const yesBtn = document.getElementById('confirm-yes');
        const noBtn = document.getElementById('confirm-no');

        titleEl.textContent = title;
        textEl.textContent = text;
        modal.classList.remove('hidden');

        const handleYes = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(true);
        };
        const handleNo = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(false);
        };
        const cleanup = () => {
            yesBtn.removeEventListener('click', handleYes);
            noBtn.removeEventListener('click', handleNo);
        };

        yesBtn.addEventListener('click', handleYes);
        noBtn.addEventListener('click', handleNo);
    });
}

window.deleteDocument = async (id) => {
    const confirmed = await showConfirm(
        'Delete Intelligence?',
        'Are you sure? This will permanently delete this document and all its chat history. This action cannot be undone.'
    );
    
    if (!confirmed) return;
    
    try {
        const res = await authFetch(`${API_BASE}/documents/${id}`, { 
            method: 'DELETE'
        });

        if (res.ok) {
            showToast('Document and history deleted.', 'success');
            
            if (activeDoc && activeDoc.id === id) {
                chatHub.classList.add('hidden');
                activeDoc = null;
            }
            
            fetchDocuments();
        } else {
            showToast('Failed to delete document.', 'error');
        }
    } catch (err) {
        showToast('Connection error.', 'error');
    }
};

/**
 * High-Fidelity MicroVortex Engine
 * Particle-driven loading animation for AI avatars
 */
class MicroVortex {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.W = 80;
        this.H = 80;
        this.cx = this.W / 2;
        this.cy = this.H / 2;
        this.time = 0;
        this.isGenerating = true;
        this.NUM = 200;
        this.particles = [];
        this.palette = [
            [20, 80, 200], [180, 200, 250], [41, 171, 226], [29, 171, 226]
        ];
        this.init();
        this.draw();
    }

    init() {
        for (let i = 0; i < this.NUM; i++) {
            const angle = Math.random() * Math.PI * 2;
            const r = 18 + Math.random() * 12; // Tight orbit around the 14px radius (28px total) avatar
            const col = this.palette[Math.floor(Math.random() * this.palette.length)];
            
            const p = {
                baseAngle: angle,
                baseR: r,
                x: 0, y: 0,
                vx: 0, vy: 0,
                size: Math.random() * 1.0 + 0.3,
                col,
                alpha: Math.random() * 0.6 + 0.2,
                speed: Math.random() * 0.04 + 0.015,
                orbitOffset: Math.random() * Math.PI * 2,
                drag: 0.85
            };

            const initialAmoeba = 1 + Math.sin(p.baseAngle * 3) * 0.1 * (p.baseR / 30);
            p.x = this.cx + Math.cos(p.baseAngle + p.orbitOffset) * (p.baseR * initialAmoeba);
            p.y = this.cy + Math.sin(p.baseAngle + p.orbitOffset) * (p.baseR * initialAmoeba);
            
            this.particles.push(p);
        }
    }

    stop() {
        this.isGenerating = false;
        if (this.canvas) this.canvas.style.opacity = '0';
    }

    draw() {
        if (!this.isGenerating) return;
        
        this.time += 0.02;
        this.ctx.clearRect(0, 0, this.W, this.H);

        const breath = 1 + 0.05 * Math.sin(this.time * 2);

        for (let i = 0; i < this.NUM; i++) {
            const p = this.particles[i];
            const orbit = this.time * p.speed * 10 + p.orbitOffset;
            const amoebaWobble = 1 + Math.sin(p.baseAngle * 3 - this.time * 3) * 0.1 * (p.baseR / 30);

            const targetX = this.cx + Math.cos(p.baseAngle + orbit) * (p.baseR * breath * amoebaWobble);
            const targetY = this.cy + Math.sin(p.baseAngle + orbit) * (p.baseR * breath * amoebaWobble);

            let fx = (targetX - p.x) * 0.1;
            let fy = (targetY - p.y) * 0.1;

            p.vx = (p.vx + fx) * p.drag;
            p.vy = (p.vy + fy) * p.drag;
            p.x += p.vx;
            p.y += p.vy;

            const distCenter = Math.hypot(p.x - this.cx, p.y - this.cy);
            const dimCenter = Math.max(0, 1 - (distCenter - 14) / 15); 
            const alpha = p.alpha * dimCenter;
            
            const [r, g, b] = p.col;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${r},${g},${b},${alpha.toFixed(2)})`;
            this.ctx.fill();
        }

        requestAnimationFrame(() => this.draw());
    }
}

// Identity Handlers
loginBtn.addEventListener('click', (e) => { e.stopPropagation(); authMode = 'login'; updateModalUI(); authModal.classList.remove('hidden'); });
signupBtn.addEventListener('click', (e) => { e.stopPropagation(); authMode = 'signup'; updateModalUI(); authModal.classList.remove('hidden'); });

logoutBtn.addEventListener('click', (e) => {
    console.log("Engram: Logout Triggered");
    e.stopPropagation();
    userDropdown.classList.add('hidden');
    logout();
});

profileBtn.addEventListener('click', (e) => {
    console.log("Engram: Profile Triggered");
    e.stopPropagation();
    if (!currentUser) return;
    userDropdown.classList.add('hidden');
    profileInfo.innerHTML = `
        <div class="profile-item"><span>Full Name</span><span>${currentUser.full_name || 'N/A'}</span></div>
        <div class="profile-item"><span>Email</span><span>${currentUser.email}</span></div>
        <div class="profile-item"><span>User ID</span><span>${currentUser.id}</span></div>
        <div class="profile-item"><span>Account Status</span><span><span class="status-badge">Active</span></span></div>
    `;
    profileModal.classList.remove('hidden');
});

modalClose.onclick = () => authModal.classList.add('hidden');
profileClose.onclick = () => profileModal.classList.add('hidden');

changePasswordBtn.onclick = async () => {
    const old_password = currentPasswordInput.value;
    const new_password = newPasswordInput.value;
    
    if (!old_password || !new_password) {
        showToast('Please fill all password fields', 'error');
        return;
    }
    
    // Loading State
    const originalText = changePasswordBtn.textContent;
    changePasswordBtn.disabled = true;
    changePasswordBtn.textContent = 'Updating...';
    
    try {
        const res = await authFetch(`${API_BASE}/auth/change-password`, {
            method: 'POST',
            body: JSON.stringify({ old_password, new_password })
        });
        
        if (res.ok) {
            showToast('Password updated successfully', 'success');
            currentPasswordInput.value = '';
            newPasswordInput.value = '';
        } else {
            const data = await res.json();
            showToast(data.detail || 'Failed to update password', 'error');
        }
    } catch (err) {
        showToast('Connection error', 'error');
    } finally {
        changePasswordBtn.disabled = false;
        changePasswordBtn.textContent = originalText;
    }
};

function updateModalUI() {
    if (authMode === 'login') {
        modalTitle.textContent = 'Welcome Back';
        nameField.classList.add('hidden');
        authSubmit.textContent = 'Login';
        modalToggleText.innerHTML = `Don't have an account? <a href="#" id="modal-toggle">Sign up</a>`;
    } else {
        modalTitle.textContent = 'Create Account';
        nameField.classList.remove('hidden');
        authSubmit.textContent = 'Sign Up';
        modalToggleText.innerHTML = `Already have an account? <a href="#" id="modal-toggle">Log in</a>`;
    }
    document.getElementById('modal-toggle').onclick = () => { authMode = (authMode === 'login' ? 'signup' : 'login'); updateModalUI(); };
}

authSubmit.onclick = async () => {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const full_name = document.getElementById('full-name').value;
    const body = authMode === 'login' ? { email, password } : { email, password, full_name };
    const endpoint = authMode === 'login' ? 'login' : 'register';
    
    // 1. Loading State
    const originalText = authSubmit.textContent;
    authSubmit.disabled = true;
    authSubmit.innerHTML = `<span class="spinner-tiny"></span> ${authMode === 'login' ? 'Authenticating...' : 'Creating Account...'}`;

    try {
        const res = await fetch(`${API_BASE}/auth/${endpoint}`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(body) 
        });
        
        if (res.ok) {
            const data = await res.json();
            authToken = data.access_token;
            refreshToken = data.refresh_token;
            localStorage.setItem('access_token', authToken);
            localStorage.setItem('refresh_token', refreshToken);
            
            authModal.classList.add('hidden');
            showToast(authMode === 'login' ? 'Welcome back!' : 'Account created!', 'success');
            await checkAuth();
        } else { 
            const errData = await res.json();
            let msg = 'Authentication failed';
            
            // Handle FastAPI's detail formats (string or validation list)
            if (typeof errData.detail === 'string') {
                msg = errData.detail;
            } else if (Array.isArray(errData.detail) && errData.detail.length > 0) {
                // Pick the first validation error message
                msg = errData.detail[0].msg || 'Validation error';
            }
            
            showToast(msg, 'error'); 
        }
    } catch (err) {
        showToast('Connection error', 'error');
    } finally {
        authSubmit.disabled = false;
        authSubmit.textContent = originalText;
    }
};

// Back to Top Visibility Logic
window.addEventListener('scroll', () => {
    const backToTop = document.getElementById('back-to-top');
    if (backToTop) {
        if (window.scrollY > 400) {
            backToTop.classList.add('visible');
        } else {
            backToTop.classList.remove('visible');
        }
    }
});
