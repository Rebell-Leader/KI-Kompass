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
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('chat-messages');
    const sendButton = document.querySelector('#chat-form button[type="submit"]');

    // Only initialize if chat elements exist
    if (!chatForm || !messageInput || !messagesContainer) {
        return;
    }

    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const message = messageInput.value.trim();
        if (!message) return;

        // Disable form while processing
        messageInput.disabled = true;
        if (sendButton) sendButton.disabled = true;

        // Add user message to chat
        addMessage(message, 'user');
        messageInput.value = '';

        // Send message to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                message: message,
                conversation_id: getCurrentConversationId()
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.response) {
                addMessage(data.response, 'assistant');
                if (data.conversation_id) {
                    setCurrentConversationId(data.conversation_id);
                }
            } else if (data.error) {
                addMessage('Sorry, I encountered an error: ' + data.error, 'assistant');
            }
        })
        .catch(error => {
            console.error('Chat error:', error);
            addMessage('Sorry, I encountered a technical error. Please try again.', 'assistant');
        })
        .finally(() => {
            // Re-enable form
            messageInput.disabled = false;
            if (sendButton) sendButton.disabled = false;
            messageInput.focus();
        });
    });
}

function addMessage(content, role) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function getCurrentConversationId() {
    return sessionStorage.getItem('conversation_id') || null;
}

function setCurrentConversationId(id) {
    sessionStorage.setItem('conversation_id', id);
}