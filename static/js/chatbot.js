/**
 * Enhanced Tender Chatbot JavaScript
 * static/js/chatbot.js
 */

class TenderChatbot {
    constructor() {
        this.isOpen = false;
        this.isLoading = false;
        this.messageHistory = [];
        this.conversationId = this.generateConversationId();
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadQuickStats();
        this.showWelcomeMessage();
    }
    
    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeElements() {
        this.toggle = document.getElementById('chatbotToggle');
        this.window = document.getElementById('chatbotWindow');
        this.close = document.getElementById('chatbotClose');
        this.messages = document.getElementById('chatbotMessages');
        this.input = document.getElementById('chatbotInput');
        this.sendButton = document.getElementById('chatbotSend');
        this.badge = document.getElementById('chatbotBadge');
        this.stats = {
            active: document.getElementById('statActive'),
            week: document.getElementById('statWeek'),
            overdue: document.getElementById('statOverdue'),
            notifications: document.getElementById('statNotifications')
        };
    }
    
    attachEventListeners() {
        // Toggle chatbot
        this.toggle.addEventListener('click', () => this.toggleChatbot());
        this.close.addEventListener('click', () => this.closeChatbot());
        
        // Send message
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize input
        this.input.addEventListener('input', () => this.autoResizeInput());
        
        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!this.window.contains(e.target) && !this.toggle.contains(e.target)) {
                if (this.isOpen) {
                    this.closeChatbot();
                }
            }
        });
    }
    
    toggleChatbot() {
        if (this.isOpen) {
            this.closeChatbot();
        } else {
            this.openChatbot();
        }
    }
    
    openChatbot() {
        this.window.classList.add('show');
        this.isOpen = true;
        this.input.focus();
        this.hideBadge();
        
        // Load fresh stats when opening
        this.loadQuickStats();
    }
    
    closeChatbot() {
        this.window.classList.remove('show');
        this.isOpen = false;
    }
    
    async loadQuickStats() {
        try {
            const response = await fetch('/api/chatbot/quick-stats');
            const data = await response.json();
            
            if (data.success) {
                this.stats.active.textContent = data.stats.active_tenders || 0;
                this.stats.week.textContent = data.stats.closing_this_week || 0;
                this.stats.overdue.textContent = data.stats.overdue || 0;
                this.stats.notifications.textContent = data.stats.notifications || 0;
                
                // Show badge if there are urgent items
                if (data.stats.overdue > 0 || data.stats.closing_this_week > 0) {
                    this.showBadge();
                }
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    showWelcomeMessage() {
        setTimeout(() => {
            this.addBotMessage(
                "👋 Hi! I'm TenderBot, your intelligent AI assistant. I can help you with:\n\n" +
                "• 📊 Analytics and insights\n" +
                "• 🔍 Search and filter tenders\n" +
                "• ⏰ Deadline tracking\n" +
                "• 📈 Performance analysis\n\n" +
                "Try asking me anything about your tenders!",
                'welcome',
                [
                    "Show performance summary",
                    "Find IT tenders",
                    "What's closing this week?",
                    "Success rate analysis"
                ]
            );
        }, 500);
    }
    
    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isLoading) return;
        
        // Add user message to chat
        this.addUserMessage(message);
        this.input.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        this.isLoading = true;
        this.sendButton.disabled = true;
        
        try {
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    conversation_id: this.conversationId
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            if (data.success) {
                this.addBotMessage(
                    data.response, 
                    data.type, 
                    data.suggestions || null, 
                    data.data
                );
                
                // Update stats if response includes new data
                if (data.type === 'stats' || data.type === 'analytics') {
                    setTimeout(() => this.loadQuickStats(), 500);
                }
            } else {
                this.addBotMessage(
                    "Sorry, I encountered an error processing your request. Please try again.",
                    'error'
                );
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addBotMessage(
                "I'm having trouble connecting right now. Please check your internet connection and try again.",
                'error'
            );
            console.error('Chatbot error:', error);
        } finally {
            this.isLoading = false;
            this.sendButton.disabled = false;
            this.input.focus();
        }
    }
    
    addUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user';
        messageElement.innerHTML = `
            <div class="message-bubble">${this.escapeHtml(message)}</div>
        `;
        
        this.messages.appendChild(messageElement);
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({ type: 'user', content: message });
    }
    
    addBotMessage(message, type = 'info', suggestions = null, data = null) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message bot';
        
        let html = `<div class="message-bubble ${type}">${this.formatMessage(message)}</div>`;
        
        // Add data display if present
        if (data && (Array.isArray(data) || typeof data === 'object')) {
            html += this.formatDataDisplay(data, type);
        }
        
        // Add suggestions if present
        if (suggestions && suggestions.length > 0) {
            html += this.formatSuggestions(suggestions);
        }
        
        messageElement.innerHTML = html;
        this.messages.appendChild(messageElement);
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({ 
            type: 'bot', 
            content: message, 
            data: data, 
            suggestions: suggestions 
        });
    }
    
    formatMessage(message) {
        // Convert markdown-style formatting
        return message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }
    
    formatDataDisplay(data, type) {
        let className = 'message-data';
        if (type === 'warning') className += ' warning';
        if (type === 'urgent') className += ' urgent';
        if (type === 'analytics' || type === 'stats') className += ' analytics';
        
        let html = `<div class="${className}">`;
        
        // Handle object data (like analytics/stats)
        if (!Array.isArray(data) && typeof data === 'object') {
            html += '<div class="stats-grid">';
            for (const [key, value] of Object.entries(data)) {
                const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `
                    <div class="stat-item">
                        <div class="stat-label">${displayKey}</div>
                        <div class="stat-value">${this.escapeHtml(String(value))}</div>
                    </div>
                `;
            }
            html += '</div>';
        }
        // Handle array data
        else if (Array.isArray(data)) {
            data.forEach(item => {
                if (typeof item === 'object') {
                    html += '<div class="data-item">';
                    
                    // Title or main identifier
                    if (item.title) {
                        html += `<strong>${this.escapeHtml(item.title)}</strong>`;
                    } else if (item.number) {
                        html += `<strong>${this.escapeHtml(item.number)}</strong>`;
                    } else if (item.category) {
                        html += `<strong>${this.escapeHtml(item.category)}</strong>`;
                    } else if (item.period) {
                        html += `<strong>${this.escapeHtml(item.period)}</strong>`;
                    }
                    
                    // Additional details
                    const details = [];
                    if (item.deadline) details.push(`⏰ ${item.deadline}`);
                    if (item.days_remaining !== undefined) {
                        const urgencyClass = item.days_remaining <= 1 ? 'text-danger' : 
                                           item.days_remaining <= 3 ? 'text-warning' : '';
                        details.push(`<span class="${urgencyClass}">📅 ${item.days_remaining} days left</span>`);
                    }
                    if (item.category && !item.title) details.push(`📁 ${item.category}`);
                    if (item.value) details.push(`💰 ${item.value}`);
                    if (item.status) details.push(`📊 ${item.status}`);
                    if (item.count) details.push(`🔢 ${item.count} tenders`);
                    if (item.won !== undefined) details.push(`✅ ${item.won} won`);
                    if (item.success_rate) details.push(`📈 ${item.success_rate} success`);
                    if (item.total) details.push(`📊 ${item.total} total`);
                    
                    if (details.length > 0) {
                        html += `<br><small>${details.join(' • ')}</small>`;
                    }
                    
                    html += '</div>';
                } else {
                    html += `<div class="data-item">${this.escapeHtml(String(item))}</div>`;
                }
            });
        }
        
        html += '</div>';
        return html;
    }
    
    formatSuggestions(suggestions) {
        let html = '<div class="suggestions">';
        suggestions.forEach(suggestion => {
            const escapedSuggestion = this.escapeHtml(suggestion).replace(/'/g, '&apos;');
            html += `<span class="suggestion-chip" onclick="tenderChatbot.sendSuggestion('${escapedSuggestion}')">${this.escapeHtml(suggestion)}</span>`;
        });
        html += '</div>';
        return html;
    }
    
    sendSuggestion(suggestion) {
        // Decode HTML entities
        const textarea = document.createElement('textarea');
        textarea.innerHTML = suggestion;
        this.input.value = textarea.value;
        this.sendMessage();
    }
    
    showTypingIndicator() {
        const typingElement = document.createElement('div');
        typingElement.className = 'typing-indicator';
        typingElement.id = 'typingIndicator';
        typingElement.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        this.messages.appendChild(typingElement);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingElement = document.getElementById('typingIndicator');
        if (typingElement) {
            typingElement.remove();
        }
    }
    
    showBadge() {
        this.badge.style.display = 'flex';
    }
    
    hideBadge() {
        this.badge.style.display = 'none';
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messages.scrollTop = this.messages.scrollHeight;
        }, 100);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    autoResizeInput() {
        // Future: implement auto-resize for multi-line input
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.tenderChatbot = new TenderChatbot();
    
    // Refresh stats every 5 minutes
    setInterval(() => {
        if (window.tenderChatbot) {
            window.tenderChatbot.loadQuickStats();
        }
    }, 300000);
});

// Add some keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to open chatbot
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (window.tenderChatbot) {
            window.tenderChatbot.openChatbot();
        }
    }
    
    // Escape to close chatbot
    if (e.key === 'Escape' && window.tenderChatbot && window.tenderChatbot.isOpen) {
        window.tenderChatbot.closeChatbot();
    }
});