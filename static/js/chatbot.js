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
    const conversationIdInput = document.getElementById('conversation-id');
    
    // Store conversation ID across page reloads
    let conversationId = conversationIdInput ? conversationIdInput.value : null;
    
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
        
        // Prepare request data with conversation ID if available
        const requestData = { 
            query: query,
            conversation_id: conversationId
        };
        
        // Send message to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
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
            addMessage('assistant', data.response);
            
            // Store the conversation ID for future requests
            conversationId = data.conversation_id;
            
            // Update hidden input with conversation ID
            if (conversationIdInput && conversationId) {
                conversationIdInput.value = conversationId;
            }
            
            // Update URL with conversation ID for permalink/sharing without page reload
            if (conversationId && window.history && window.history.replaceState) {
                const url = new URL(window.location);
                url.searchParams.set('conversation_id', conversationId);
                window.history.replaceState({}, '', url);
            }
            
            // Re-enable input and button
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        })
        .catch(error => {
            // Remove loading indicator
            removeLoadingIndicator(loadingId);
            
            // Add error message
            addMessage('assistant', 'Sorry, I encountered an error. Please try again later.');
            
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
    
    // Check if we need to add an initial greeting (only if there are no messages)
    if (chatMessages.children.length === 0) {
        addMessage('assistant', 'Hello! I\'m your KI Kompass assistant. How can I help you with your relocation to Munich today?');
    }
}

/**
 * Add a message to the chat
 * @param {string} type - 'user' or 'assistant'
 * @param {string} text - Message text
 */
function addMessage(type, text) {
    const chatMessages = document.getElementById('chat-messages');
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type === 'user' ? 'message-user' : 'message-assistant');
    
    // Create content container
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    
    // Process text for links and formatting
    let processedText = text
        .replace(/\n/g, '<br>')
        // Convert URLs to clickable links
        .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    contentDiv.innerHTML = processedText;
    messageDiv.appendChild(contentDiv);
    
    // Add timestamp
    const timestamp = document.createElement('div');
    timestamp.classList.add('message-timestamp');
    
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
    loadingDiv.classList.add('message', 'message-assistant', 'loading');
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