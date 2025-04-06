/**
 * KI Kompass - Chatbot JavaScript
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    initChatbot();
});

/**
 * Initialize chatbot functionality
 */
function initChatbot() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');
    
    if (!chatForm || !chatInput || !chatMessages) {
        return;
    }
    
    // Add event listener to form submit
    chatForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const query = chatInput.value.trim();
        if (!query) return;
        
        // Add user message to chat
        addMessage('user', query);
        
        // Clear input
        chatInput.value = '';
        
        // Disable input and button while processing
        chatInput.disabled = true;
        sendButton.disabled = true;
        
        // Add loading indicator
        const loadingId = addLoadingIndicator();
        
        // Send message to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicator
            removeLoadingIndicator(loadingId);
            
            // Add AI response to chat
            addMessage('ai', data.response);
            
            // Re-enable input and button
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        })
        .catch(error => {
            // Remove loading indicator
            removeLoadingIndicator(loadingId);
            
            // Add error message
            addMessage('ai', 'Sorry, I encountered an error. Please try again later.');
            
            console.error('Error:', error);
            
            // Re-enable input and button
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        });
    });
    
    // Add event listener for input keydown
    chatInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // Focus input on page load
    chatInput.focus();
    
    // Add initial greeting
    addMessage('ai', 'Hello! I\'m your KI Kompass assistant. How can I help you with your relocation to Munich today?');
}

/**
 * Add a message to the chat
 * @param {string} type - 'user' or 'ai'
 * @param {string} text - Message text
 */
function addMessage(type, text) {
    const chatMessages = document.getElementById('chat-messages');
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type === 'user' ? 'message-user' : 'message-ai');
    
    // Process text for links and formatting
    let processedText = text
        .replace(/\n/g, '<br>')
        // Convert URLs to clickable links
        .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    messageDiv.innerHTML = processedText;
    
    // Add timestamp
    const timestamp = document.createElement('div');
    timestamp.classList.add('message-meta');
    
    const now = new Date();
    timestamp.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.appendChild(timestamp);
    
    // Add to chat and scroll to bottom
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    
    // Add animation
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateY(10px)';
    messageDiv.style.transition = 'opacity 0.3s, transform 0.3s';
    
    setTimeout(() => {
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    }, 10);
}

/**
 * Add loading indicator to chat
 * @returns {string} ID of the loading indicator
 */
function addLoadingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    
    const loadingId = 'loading-' + Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.classList.add('message', 'message-ai', 'loading');
    loadingDiv.id = loadingId;
    
    loadingDiv.innerHTML = `
        <div class="loading-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    `;
    
    // Style the dots
    const style = document.createElement('style');
    style.textContent = `
        .loading-dots {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .dot {
            width: 8px;
            height: 8px;
            background-color: #6C757D;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 1.5s infinite ease-in-out;
        }
        .dot:nth-child(2) {
            animation-delay: 0.3s;
        }
        .dot:nth-child(3) {
            animation-delay: 0.6s;
        }
        @keyframes pulse {
            0%, 100% {
                transform: scale(0.7);
                opacity: 0.5;
            }
            50% {
                transform: scale(1);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
    
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();
    
    return loadingId;
}

/**
 * Remove loading indicator from chat
 * @param {string} loadingId - ID of the loading indicator
 */
function removeLoadingIndicator(loadingId) {
    const loadingDiv = document.getElementById(loadingId);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
