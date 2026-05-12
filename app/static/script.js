const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatMessages = document.getElementById('chat-messages');
const clearBtn = document.getElementById('clear-chat');

// Add a message to the UI
function appendMessage(role, text) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', role);
    
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    contentDiv.textContent = text;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show typing indicator
function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('message', 'bot', 'typing-container');
    typingDiv.innerHTML = `
        <div class="typing">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv;
}

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;

    // Clear input
    userInput.value = '';
    
    // User message
    appendMessage('user', message);
    
    // Typing indicator
    const typingIndicator = showTyping();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        typingIndicator.remove();
        
        if (data.response) {
            appendMessage('bot', data.response);
        } else {
            appendMessage('bot', "Xin lỗi, đã có lỗi xảy ra.");
        }
    } catch (error) {
        typingIndicator.remove();
        appendMessage('bot', "Không thể kết nối với máy chủ AI.");
        console.error(error);
    }
});

// Clear chat
clearBtn.addEventListener('click', () => {
    chatMessages.innerHTML = `
        <div class="message system">
            <div class="message-content">
                Lịch sử chat đã được xóa. Tôi có thể giúp gì tiếp cho bạn?
            </div>
        </div>
    `;
});
