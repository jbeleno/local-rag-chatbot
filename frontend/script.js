// ============================================
// CONFIGURATION AND GLOBAL VARIABLES
// ============================================
const API_BASE_URL = 'http://localhost:8000/api';
let currentMode = 'docs'; // 'docs' or 'hybrid'
let documents = [];
let healthStatus = {
    backend: false,
    searchEngine: null
};
let currentSessionId = null; // Current session ID
let sessions = []; // List of all sessions

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Setup event listeners
    setupEventListeners();
    
    // Load documents
    await loadDocuments();
    
    // Load sessions
    await loadSessions();
    
    // Check system health
    await checkHealth();
    
    // Check health periodically
    setInterval(checkHealth, 30000); // Every 30 seconds
    
    // Update placeholder according to mode
    updateInputPlaceholder();
    
    // Setup language selector
    const languageSelector = document.getElementById('languageSelector');
    if (languageSelector) {
        languageSelector.value = getLanguage();
        languageSelector.addEventListener('change', (e) => {
            setLanguage(e.target.value);
        });
    }
    
    // Listen for language changes
    document.addEventListener('languageChanged', () => {
        updateInputPlaceholder();
    });
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    // Selector de modo
    document.getElementById('modeDocs').addEventListener('click', () => toggleMode('docs'));
    document.getElementById('modeHybrid').addEventListener('click', () => toggleMode('hybrid'));
    
    // Botón nuevo chat (header)
    document.getElementById('newChatBtn').addEventListener('click', createNewChat);
    
    // Botón nuevo chat (sidebar)
    document.getElementById('newChatSidebarBtn').addEventListener('click', createNewChat);
    
    // Toggle sidebar de chats
    document.getElementById('chatsSidebarToggle').addEventListener('click', toggleChatsSidebar);
    
    // Botón enviar
    document.getElementById('sendBtn').addEventListener('click', handleSendMessage);
    
    // Input de chat (Enter para enviar, Shift+Enter para nueva línea)
    const chatInput = document.getElementById('chatInput');
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
    });
    
    // Subida de archivos
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    
    uploadBtn.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(Array.from(e.target.files));
        }
    });
    
    // Drag & drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer.files).filter(file => 
            file.type === 'application/pdf' || 
            file.type === 'text/plain' || 
            file.name.endsWith('.docx')
        );
        if (files.length > 0) {
            handleFileUpload(files);
        }
    });
    
    // Toggle sidebar
    document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);
    
    // Toggle sources panel
    document.getElementById('sourcesToggle').addEventListener('click', toggleSourcesPanel);
}

// ============================================
// GESTIÓN DE MODO
// ============================================
function toggleMode(mode) {
    if (currentMode === mode) return;
    
    currentMode = mode;
    updateUIMode();
    updateInputPlaceholder();
    
    const modeName = mode === 'docs' ? t('documentation') : t('hybrid');
    showNotification(`${t('modeChanged')} ${modeName}`, 'info');
}

function updateUIMode() {
    // Actualizar botones
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`mode${currentMode === 'docs' ? 'Docs' : 'Hybrid'}`).classList.add('active');
}

function updateInputPlaceholder() {
    const input = document.getElementById('chatInput');
    if (currentMode === 'docs') {
        input.placeholder = t('placeholderDocs');
    } else {
        input.placeholder = t('placeholderHybrid');
    }
}

// ============================================
// GESTIÓN DE MENSAJES
// ============================================
async function handleSendMessage() {
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    
    if (!query) return;
    
    // Crear sesión si no existe
    if (!currentSessionId) {
        currentSessionId = generateSessionId();
        await createSession(currentSessionId);
    }
    
    // Limpiar input
    input.value = '';
    input.style.height = 'auto';
    
    // Ocultar mensaje de bienvenida
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    // Agregar mensaje del usuario
    appendMessage('user', query);
    
    // Mostrar loading
    showLoading();
    
    try {
        // Usar endpoint de chat con memoria
        const response = await fetch(`${API_BASE_URL}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                query: query,
                session_id: currentSessionId,
                mode: currentMode  // Incluir el modo actual (docs o hybrid)
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
            // Add bot response
            appendMessage('bot', data.answer, {
                sources: data.sources || []
            });
            
            // Update sources panel (include web sources if hybrid mode)
            updateSourcesPanel({
                sources_docs: data.sources || [],
                sources_web: data.sources_web || [],
                web_results: data.web_results || []
            });
            
            // Update session list
            await loadSessions();
            
        } catch (error) {
            console.error('Error sending message:', error);
            appendMessage('bot', `${t('errorProcessing')}: ${error.message}`, { error: true });
            showNotification(t('errorProcessing'), 'error');
        } finally {
            hideLoading();
            input.focus();
        }
    }

function appendMessage(type, content, metadata = {}, autoScroll = true) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    if (type === 'user') {
        messageDiv.innerHTML = `
            <div class="message-content">${escapeHtml(content)}</div>
            <div class="message-footer">
                <span class="message-time">${getCurrentTime()}</span>
            </div>
        `;
    } else {
        // Mensaje del bot
        let badgesHtml = '';
        if (metadata.sources && metadata.sources.length > 0) {
            badgesHtml += '<span class="badge mode-docs">Docs</span>';
        }
        
        const formattedContent = formatMarkdown(content);
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <div class="message-badges">${badgesHtml}</div>
            </div>
            <div class="message-content">${formattedContent}</div>
            <div class="message-footer">
                <span class="message-time">${getCurrentTime()}</span>
                <div class="message-actions">
                    <button class="message-action" onclick="copyToClipboard(this)" title="Copiar">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                            <rect x="5" y="5" width="8" height="8" rx="1"/>
                            <path d="M3 7V5a2 2 0 0 1 2-2h2"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }
    
    chatContainer.appendChild(messageDiv);
    if (autoScroll) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function formatMarkdown(text) {
    // Convertir markdown básico a HTML
    let html = escapeHtml(text);
    
    // Negritas **texto**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Listas con guiones
    html = html.replace(/^\- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // URLs
    html = html.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    
    // Saltos de línea
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

function copyToClipboard(button) {
    const messageContent = button.closest('.message').querySelector('.message-content');
    const text = messageContent.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Text copied to clipboard', 'success');
    }).catch(() => {
        showNotification('Error copying', 'error');
    });
}

// ============================================
// GESTIÓN DE DOCUMENTOS
// ============================================
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/list`);
        if (!response.ok) throw new Error('Error al cargar documentos');
        
        const data = await response.json();
        documents = (data.documents || []).map(doc => ({
            document_id: doc.id,
            filename: doc.filename,
            uploaded_at: doc.uploaded_at
        }));
        
        renderDocumentsList();
        updateDocumentCount();
    } catch (error) {
        console.error('Error al cargar documentos:', error);
        showNotification(t('errorLoadingDocuments'), 'error');
    }
}

function renderDocumentsList() {
    const listContainer = document.getElementById('documentsList');
    
    if (documents.length === 0) {
        listContainer.innerHTML = '<p class="empty-state">No hay documentos cargados</p>';
        return;
    }
    
    listContainer.innerHTML = documents.map(doc => {
        const icon = getFileIcon(doc.filename);
        const date = new Date(doc.uploaded_at).toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        return `
            <div class="document-item">
                <span class="document-icon">${icon}</span>
                <div class="document-info">
                    <div class="document-name" title="${doc.filename}">${doc.filename}</div>
                    <div class="document-meta">${date}</div>
                </div>
                <button class="document-delete" onclick="deleteDocument('${doc.document_id}')" title="Eliminar">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M3 4h10M6 4V2a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2m-4 4v4m4-4v4M5 4l1 8h4l1-8"/>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': '•',
        'txt': '•',
        'docx': '•',
        'doc': '•'
    };
    return icons[ext] || '•';
}

async function handleFileUpload(files) {
    const progressContainer = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Validate file type
        if (!isValidFileType(file)) {
            showNotification(`Invalid file type: ${file.name}`, 'error');
            continue;
        }
        
        // Show progress
        progressContainer.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = `${t('uploading')} ${file.name}...`;
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${API_BASE_URL}/documents/upload`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || t('errorUploading'));
            }
            
            // Simulate progress
            let progress = 0;
            const interval = setInterval(() => {
                progress += 10;
                progressFill.style.width = progress + '%';
                if (progress >= 100) {
                    clearInterval(interval);
                }
            }, 100);
            
            await response.json();
            
            progressFill.style.width = '100%';
            progressText.textContent = `${file.name} ${t('documentUploaded')}`;
            
            // Update list
            await loadDocuments();
            
            showNotification(`${t('documentUploaded')}: ${file.name}`, 'success');
            
            // Hide progress after a moment
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 2000);
            
        } catch (error) {
            console.error('Error uploading file:', error);
            showNotification(`${t('errorUploading')}: ${file.name} - ${error.message}`, 'error');
            progressContainer.style.display = 'none';
        }
    }
    
    // Limpiar input
    document.getElementById('fileInput').value = '';
}

function isValidFileType(file) {
    const validTypes = ['application/pdf', 'text/plain'];
    const validExtensions = ['.pdf', '.txt', '.docx'];
    const fileName = file.name.toLowerCase();
    
    return validTypes.includes(file.type) || 
           validExtensions.some(ext => fileName.endsWith(ext));
}

async function deleteDocument(documentId) {
    showModal(
        t('confirmMessage'),
        async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    throw new Error(t('errorUploading'));
                }
                
                await loadDocuments();
                showNotification(t('documentDeleted'), 'success');
            } catch (error) {
                console.error('Error deleting document:', error);
                showNotification(t('errorUploading'), 'error');
            }
        }
    );
}

function updateDocumentCount() {
    document.getElementById('docCount').textContent = documents.length;
}

// ============================================
// PANEL DE FUENTES
// ============================================
function updateSourcesPanel(data) {
    const sourcesContent = document.getElementById('sourcesContent');
    
    let html = '';
    
    // Document sources
    if (data.sources_docs && data.sources_docs.length > 0) {
        const docSources = documents.filter(doc => 
            data.sources_docs.includes(doc.document_id)
        );
        
        html += `
            <div class="source-section">
                <div class="source-section-title">
                    <span>${t('documentSources')} (${docSources.length})</span>
                </div>
                <div class="source-list">
                    ${docSources.map(doc => `
                        <div class="source-item">
                            <div class="source-item-doc">${doc.filename}</div>
                            <div class="source-item-meta">ID: ${doc.document_id.substring(0, 8)}...</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Web sources
    if (data.sources_web && data.sources_web.length > 0) {
        html += `
            <div class="source-section">
                <div class="source-section-title">
                    <span>${t('webSources')} (${data.sources_web.length})</span>
                </div>
                <div class="source-list">
                    ${data.sources_web.map((url, idx) => {
                        const webResult = data.web_results && data.web_results[idx];
                        const title = webResult ? webResult.title : url;
                        return `
                            <div class="source-item">
                                <a href="${url}" target="_blank" rel="noopener noreferrer">
                                    ${title || url}
                                </a>
                                ${webResult && webResult.snippet ? `
                                    <div class="source-item-meta">${webResult.snippet.substring(0, 100)}...</div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
    
    if (!html) {
        html = `<p class="empty-state">${t('noSources')}</p>`;
    }
    
    sourcesContent.innerHTML = html;
}

function toggleSourcesPanel() {
    const panel = document.getElementById('sourcesPanel');
    const mainContainer = document.querySelector('.main-container');
    const toggle = document.getElementById('sourcesToggle');
    
    panel.classList.toggle('open');
    mainContainer.classList.toggle('sources-expanded');
    
    const isExpanded = mainContainer.classList.contains('sources-expanded');
    toggle.querySelector('span').textContent = isExpanded ? '▶' : '◀';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContainer = document.querySelector('.main-container');
    const toggle = document.getElementById('sidebarToggle');
    
    sidebar.classList.toggle('open');
    mainContainer.classList.toggle('sidebar-collapsed');
    
    const isCollapsed = mainContainer.classList.contains('sidebar-collapsed');
    toggle.querySelector('span').textContent = isCollapsed ? '▶' : '◀';
}

// ============================================
// SALUD DEL SISTEMA
// ============================================
async function checkHealth() {
    try {
        const response = await fetch('http://localhost:8000/health');
        if (!response.ok) throw new Error('Backend no disponible');
        
        const health = await response.json();
        healthStatus.backend = health.status === 'healthy';
        
        // Actualizar indicador de backend
        const backendStatus = document.getElementById('backendStatus');
        if (healthStatus.backend) {
            backendStatus.classList.add('online');
        } else {
            backendStatus.classList.remove('online');
        }
        
        // Actualizar indicador de motor de búsqueda
        if (health.web_search && health.web_search.duckduckgo) {
            const searchStatus = health.web_search.duckduckgo.status;
            if (searchStatus === 'available') {
                document.getElementById('searchEngineStatus').style.display = 'flex';
                document.getElementById('searchEngineText').textContent = 'DuckDuckGo';
            }
        }
        
    } catch (error) {
        console.error('Error al verificar salud:', error);
        healthStatus.backend = false;
        document.getElementById('backendStatus').classList.remove('online');
    }
}

// ============================================
// LOADING INDICATOR
// ============================================
function showLoading() {
    const loading = document.getElementById('loadingIndicator');
    const loadingText = document.getElementById('loadingText');
    
    loadingText.textContent = t('thinking');
    loading.style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingIndicator').style.display = 'none';
}

// ============================================
// GESTIÓN DE CHATS Y SESIONES
// ============================================
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

async function createSession(sessionId) {
    try {
        // La sesión se crea automáticamente cuando se envía el primer mensaje
        // Solo necesitamos actualizar la UI
        currentSessionId = sessionId;
        await loadSessions();
    } catch (error) {
        console.error('Error al crear sesión:', error);
    }
}

async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/sessions`);
        if (!response.ok) throw new Error('Error al cargar sesiones');
        
        const data = await response.json();
        sessions = data.sessions || [];
        renderChatsList();
    } catch (error) {
        console.error('Error al cargar sesiones:', error);
        sessions = [];
        renderChatsList();
    }
}

function renderChatsList() {
    const chatsList = document.getElementById('chatsList');
    
    if (sessions.length === 0) {
        chatsList.innerHTML = `<p class="empty-state">${t('noChats')}</p>`;
        return;
    }
    
    chatsList.innerHTML = sessions.map(session => {
        const date = new Date(session.updated_at);
        const dateStr = date.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const isActive = session.session_id === currentSessionId;
        const title = session.message_count > 0 
            ? `Chat ${sessions.indexOf(session) + 1}` 
            : t('newChat');
        
        return `
            <div class="chat-item ${isActive ? 'active' : ''}" data-session-id="${session.session_id}">
                <div class="chat-item-actions">
                    <button class="chat-item-action" onclick="deleteChat('${session.session_id}', event)" title="Eliminar">
                        ×
                    </button>
                </div>
                <div class="chat-item-title" onclick="selectChat('${session.session_id}')">${title}</div>
                <div class="chat-item-meta">
                    <span>${session.message_count} msgs</span>
                    <span>${dateStr}</span>
                </div>
            </div>
        `;
    }).join('');
}

async function selectChat(sessionId) {
    if (currentSessionId === sessionId) return;
    
    currentSessionId = sessionId;
    renderChatsList();
    
    // Cargar historial
    await loadChatHistory(sessionId);
}

async function loadChatHistory(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`);
        if (!response.ok) throw new Error('Error al cargar historial');
        
        const data = await response.json();
        const chatContainer = document.getElementById('chatContainer');
        
        // Limpiar contenedor
        chatContainer.innerHTML = '';
        
        // Ocultar mensaje de bienvenida si no hay mensajes
        if (data.messages.length === 0) {
            chatContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Chatbot RAG</h2>
                    <p>Puedo ayudarte con:</p>
                    <ul>
                        <li>Consultar tus documentos locales</li>
                        <li>Buscar información en internet</li>
                        <li>Responder preguntas combinando ambas fuentes</li>
                    </ul>
                    <p class="welcome-hint">Selecciona un modo y comienza a preguntar.</p>
                </div>
            `;
            return;
        }
        
        // Mostrar mensajes
        data.messages.forEach(msg => {
            const metadata = msg.metadata || {};
            appendMessage(msg.role, msg.content, {
                sources: metadata.sources || []
            }, false); // false = no hacer scroll automático
        });
        
        // Scroll al final
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
    } catch (error) {
        console.error('Error al cargar historial:', error);
        showNotification(t('errorLoadingSessions'), 'error');
    }
}

async function deleteChat(sessionId, event) {
    event.stopPropagation();
    
    showModal(
        t('confirmMessage'),
        async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) throw new Error('Error al eliminar chat');
                
                // Si era el chat actual, crear uno nuevo
                if (currentSessionId === sessionId) {
                    currentSessionId = null;
                    const chatContainer = document.getElementById('chatContainer');
                    chatContainer.innerHTML = `
                        <div class="welcome-message">
                            <h2>Chatbot RAG</h2>
                            <p>Puedo ayudarte con:</p>
                            <ul>
                                <li>Consultar tus documentos locales</li>
                                <li>Buscar información en internet</li>
                                <li>Responder preguntas combinando ambas fuentes</li>
                            </ul>
                            <p class="welcome-hint">Selecciona un modo y comienza a preguntar.</p>
                        </div>
                    `;
                }
                
                await loadSessions();
                showNotification(t('sessionDeleted'), 'success');
            } catch (error) {
                console.error('Error deleting chat:', error);
                showNotification(t('errorLoadingSessions'), 'error');
            }
        }
    );
}

function createNewChat() {
    currentSessionId = null;
    const chatContainer = document.getElementById('chatContainer');
    
    // Limpiar mensajes
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Chatbot RAG</h2>
            <p>Puedo ayudarte con:</p>
            <ul>
                <li>Consultar tus documentos locales</li>
                <li>Buscar información en internet</li>
                <li>Responder preguntas combinando ambas fuentes</li>
            </ul>
            <p class="welcome-hint">Selecciona un modo y comienza a preguntar.</p>
        </div>
    `;
    
    // Limpiar panel de fuentes
    const sourcesContent = document.getElementById('sourcesContent');
    sourcesContent.innerHTML = '<p class="empty-state">Las fuentes aparecerán aquí después de hacer una consulta</p>';
    
    // Ocultar loading si está visible
    hideLoading();
    
    // Actualizar lista de chats
    renderChatsList();
    
    // Mostrar notificación
    showNotification(t('sessionCreated'), 'success');
    
    // Enfocar input
    document.getElementById('chatInput').focus();
}

function toggleChatsSidebar() {
    const mainContainer = document.querySelector('.main-container');
    const chatsSidebar = document.getElementById('chatsSidebar');
    const toggle = document.getElementById('chatsSidebarToggle');
    
    // En móviles, usar clase 'open' para mostrar/ocultar
    if (window.innerWidth <= 768) {
        chatsSidebar.classList.toggle('open');
    } else {
        mainContainer.classList.toggle('chats-collapsed');
    }
    
    const isCollapsed = mainContainer.classList.contains('chats-collapsed') || 
                       (window.innerWidth <= 768 && !chatsSidebar.classList.contains('open'));
    toggle.querySelector('span').textContent = isCollapsed ? '▶' : '‹';
}

// ============================================
// MODAL
// ============================================
function showModal(message, onConfirm) {
    const overlay = document.getElementById('modalOverlay');
    const modalMessage = document.getElementById('modalMessage');
    const confirmBtn = document.getElementById('modalConfirm');
    const cancelBtn = document.getElementById('modalCancel');
    
    modalMessage.textContent = message;
    overlay.style.display = 'flex';
    
    // Remover listeners anteriores
    const newConfirmBtn = confirmBtn.cloneNode(true);
    const newCancelBtn = cancelBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    
    // Agregar nuevos listeners
    newConfirmBtn.addEventListener('click', () => {
        hideModal();
        if (onConfirm) onConfirm();
    });
    
    newCancelBtn.addEventListener('click', hideModal);
    
    // Cerrar al hacer clic fuera del modal
    const overlayClickHandler = (e) => {
        if (e.target === overlay) {
            hideModal();
            overlay.removeEventListener('click', overlayClickHandler);
        }
    };
    overlay.addEventListener('click', overlayClickHandler);
    
    // Cerrar con Escape
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            hideModal();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

function hideModal() {
    const overlay = document.getElementById('modalOverlay');
    overlay.style.display = 'none';
}

// ============================================
// NOTIFICACIONES
// ============================================
function showNotification(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '×',
        warning: '!',
        info: 'i'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <div class="toast-content">
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    container.appendChild(toast);
    
    // Auto-remover después de la duración
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

