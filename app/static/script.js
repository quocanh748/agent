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
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Lỗi máy chủ");
        }
        
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
        console.error('Chat Error:', error);
        
        if (error.message === "Failed to fetch") {
            appendMessage('bot', "Không thể kết nối với máy chủ AI. Vui lòng đảm bảo bạn đang truy cập qua http://localhost:8000");
        } else {
            appendMessage('bot', `Lỗi: ${error.message}`);
        }
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
