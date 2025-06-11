document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatWindow = document.getElementById('chat-window');
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const conversationList = document.getElementById('conversation-list');
    const modelSelector = document.getElementById('model-selector');
    const chatContainer = document.getElementById('chat-container');
    const sendButton = document.querySelector('#chat-form button');
    const uploadButton = document.querySelector('#upload-form button');

    const currentConversationId = chatContainer ? chatContainer.dataset.conversationId : null;
    let isModelLoading = false;

    // --- Helper function to add messages to the chat window ---
    function addMessage(text, className, isHtml = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${className}`;
        if (isHtml) {
            messageDiv.innerHTML = text;
        } else {
            const p = document.createElement('p');
            p.textContent = text;
            messageDiv.appendChild(p);
        }
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return messageDiv;
    }

    // --- Reusable function to handle the model loading sequence ---
    async function handleModelLoad(modelName) {
        if (!modelName || isModelLoading) {
            return;
        }
        isModelLoading = true;
        addMessage(`System is loading model: ${modelName}. Please wait...`, 'system-message');
        toggleAllInputs(true);

        try {
            const response = await fetch('/api/load_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelName })
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load model.');
            }
            addMessage(`Model "${modelName}" is ready. You can now start the chat.`, 'system-message');
        } catch (error) {
            addMessage(`Error: ${error.message}`, 'error-message');
            loadModels(false); // Attempt to reset the model list on failure
        } finally {
            toggleAllInputs(false);
            isModelLoading = false;
        }
    }

    // --- Data Loading Functions ---
    async function loadModels(triggerInitialLoad = true) {
        if (!modelSelector) return;
        try {
            const response = await fetch('/api/models');
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch models.');
            
            modelSelector.innerHTML = '';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = model.name;
                modelSelector.appendChild(option);
            });
            
            modelSelector.value = data.default_model;

            if (triggerInitialLoad && data.default_model) {
                await handleModelLoad(data.default_model);
            }
        } catch (error) {
            console.error('Error loading models:', error);
        }
    }

    async function loadConversations() {
        // ... (function is unchanged)
    }

    async function loadMessagesForCurrentConversation() {
        // ... (function is unchanged)
    }
    
    // --- Helper to toggle ALL input forms and the load button ---
    function toggleAllInputs(disabled) {
        messageInput.disabled = disabled;
        sendButton.disabled = disabled;
        fileInput.disabled = disabled;
        uploadButton.disabled = disabled;
        modelSelector.disabled = disabled;
    }

    // --- Event Listeners ---
    if (modelSelector) {
        modelSelector.addEventListener('change', () => {
            handleModelLoad(modelSelector.value);
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const userMessage = messageInput.value.trim();
            if (!userMessage) return;

            addMessage(userMessage, 'user-message');
            messageInput.value = '';
            const aiThinkingMessage = addMessage('<p>...</p>', 'ai-message', true);

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: userMessage,
                        conversation_id: currentConversationId
                    }),
                });
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText || `HTTP error! status: ${response.status}`);
                }
                aiThinkingMessage.innerHTML = await response.text();
            } catch (error) {
                aiThinkingMessage.innerHTML = `<p class="error-message">${error.message}</p>`;
            }
        });
    }

    // ... (uploadForm event listener is unchanged)

    // --- Initial Page Load ---
    async function initializeChat() {
        await loadMessagesForCurrentConversation();
        await loadConversations();
        await loadModels();
    }

    initializeChat();
});