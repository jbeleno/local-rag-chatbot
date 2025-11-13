/**
 * Simple i18n system for bilingual support (ES/EN)
 * No external dependencies
 */

const i18n = {
    es: {
        // Header
        newChat: "Nuevo Chat",
        documentation: "Documentación",
        hybrid: "Híbrido",
        backend: "Backend:",
        docs: "Docs:",
        search: "Búsqueda:",
        
        // Sidebars
        chats: "Chats",
        documents: "Documentos",
        noChats: "No hay chats",
        noDocuments: "No hay documentos cargados",
        
        // Upload
        uploadDocuments: "Subir Documentos",
        dragFilesHere: "Arrastra archivos aquí",
        clickToSelect: "o haz clic para seleccionar",
        uploading: "Subiendo...",
        
        // Chat
        welcomeTitle: "Chatbot RAG",
        welcomeHelp: "Puedo ayudarte con:",
        welcomeItem1: "Consultar tus documentos locales",
        welcomeItem2: "Buscar información en internet",
        welcomeItem3: "Responder preguntas combinando ambas fuentes",
        welcomeHint: "Selecciona un modo y comienza a preguntar.",
        placeholderDocs: "Pregunta sobre tus documentos...",
        placeholderHybrid: "Pregunta sobre tus documentos o busca en internet...",
        sendMessage: "Enviar mensaje",
        inputHint: "Presiona Enter para enviar, Shift+Enter para nueva línea",
        thinking: "Pensando...",
        
        // Sources
        sources: "Fuentes",
        sourcesPlaceholder: "Las fuentes aparecerán aquí después de hacer una consulta",
        documentSources: "Fuentes de documentos:",
        webSources: "Fuentes web:",
        noSources: "No hay fuentes disponibles",
        
        // Modal
        confirmAction: "Confirmar acción",
        confirmMessage: "¿Estás seguro de que quieres realizar esta acción?",
        cancel: "Cancelar",
        accept: "Aceptar",
        delete: "Eliminar",
        
        // Notifications
        modeChanged: "Modo cambiado a",
        documentUploaded: "Documento subido exitosamente",
        documentDeleted: "Documento eliminado",
        errorUploading: "Error al subir documento",
        errorLoadingDocuments: "Error al cargar documentos",
        errorLoadingSessions: "Error al cargar sesiones",
        errorSendingMessage: "Error al enviar mensaje",
        errorProcessing: "Error al procesar tu consulta",
        sessionCreated: "Nueva sesión creada",
        sessionLoaded: "Sesión cargada",
        sessionDeleted: "Sesión eliminada",
        
        // Time
        justNow: "Hace un momento",
        minutesAgo: "hace {n} minutos",
        hoursAgo: "hace {n} horas",
        daysAgo: "hace {n} días",
        
        // Language selector
        language: "Idioma",
        spanish: "Español",
        english: "English"
    },
    en: {
        // Header
        newChat: "New Chat",
        documentation: "Documentation",
        hybrid: "Hybrid",
        backend: "Backend:",
        docs: "Docs:",
        search: "Search:",
        
        // Sidebars
        chats: "Chats",
        documents: "Documents",
        noChats: "No chats",
        noDocuments: "No documents loaded",
        
        // Upload
        uploadDocuments: "Upload Documents",
        dragFilesHere: "Drag files here",
        clickToSelect: "or click to select",
        uploading: "Uploading...",
        
        // Chat
        welcomeTitle: "RAG Chatbot",
        welcomeHelp: "I can help you with:",
        welcomeItem1: "Query your local documents",
        welcomeItem2: "Search information on the internet",
        welcomeItem3: "Answer questions combining both sources",
        welcomeHint: "Select a mode and start asking.",
        placeholderDocs: "Ask about your documents...",
        placeholderHybrid: "Ask about your documents or search the internet...",
        sendMessage: "Send message",
        inputHint: "Press Enter to send, Shift+Enter for new line",
        thinking: "Thinking...",
        
        // Sources
        sources: "Sources",
        sourcesPlaceholder: "Sources will appear here after making a query",
        documentSources: "Document sources:",
        webSources: "Web sources:",
        noSources: "No sources available",
        
        // Modal
        confirmAction: "Confirm action",
        confirmMessage: "Are you sure you want to perform this action?",
        cancel: "Cancel",
        accept: "Accept",
        delete: "Delete",
        
        // Notifications
        modeChanged: "Mode changed to",
        documentUploaded: "Document uploaded successfully",
        documentDeleted: "Document deleted",
        errorUploading: "Error uploading document",
        errorLoadingDocuments: "Error loading documents",
        errorLoadingSessions: "Error loading sessions",
        errorSendingMessage: "Error sending message",
        errorProcessing: "Error processing your query",
        sessionCreated: "New session created",
        sessionLoaded: "Session loaded",
        sessionDeleted: "Session deleted",
        
        // Time
        justNow: "Just now",
        minutesAgo: "{n} minutes ago",
        hoursAgo: "{n} hours ago",
        daysAgo: "{n} days ago",
        
        // Language selector
        language: "Language",
        spanish: "Español",
        english: "English"
    }
};

// Current language (default: detect from browser or use Spanish)
let currentLanguage = localStorage.getItem('language') || 
                     (navigator.language.startsWith('es') ? 'es' : 'en');

/**
 * Get translation for a key
 * @param {string} key - Translation key
 * @param {object} params - Parameters to replace in translation (e.g., {n: 5})
 * @returns {string} Translated text
 */
function t(key, params = {}) {
    const translation = i18n[currentLanguage]?.[key] || key;
    
    // Replace parameters
    if (Object.keys(params).length > 0) {
        return translation.replace(/\{(\w+)\}/g, (match, paramKey) => {
            return params[paramKey] !== undefined ? params[paramKey] : match;
        });
    }
    
    return translation;
}

/**
 * Set language
 * @param {string} lang - Language code ('es' or 'en')
 */
function setLanguage(lang) {
    if (i18n[lang]) {
        currentLanguage = lang;
        localStorage.setItem('language', lang);
        updateUI();
    }
}

/**
 * Get current language
 * @returns {string} Current language code
 */
function getLanguage() {
    return currentLanguage;
}

/**
 * Update all UI elements with current language
 */
function updateUI() {
    // Update HTML lang attribute
    document.documentElement.lang = currentLanguage;
    
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const text = t(key);
        
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            if (element.hasAttribute('placeholder') || element.hasAttribute('data-i18n-placeholder')) {
                element.placeholder = text;
            } else {
                element.value = text;
            }
        } else {
            element.textContent = text;
        }
    });
    
    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        element.placeholder = t(key);
    });
    
    // Update title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(element => {
        const key = element.getAttribute('data-i18n-title');
        element.title = t(key);
    });
    
    // Trigger custom event for components that need to update
    document.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: currentLanguage } 
    }));
}

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateUI);
} else {
    updateUI();
}

