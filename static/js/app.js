/**
 * Main Application Entry Point
 * Initializes the app and handles user interactions
 */

import {
    state,
    elements,
    initElements,
    setCurrentConversation,
    setCurrentAgent
} from './state.js';

import {
    fetchAgents,
    fetchConversations,
    fetchConversation,
    createConversation as apiCreateConversation,
    deleteConversation as apiDeleteConversation,
    sendMessage as apiSendMessage,
    processStreamingResponse
} from './api.js';

import {
    showWelcomeScreen,
    setComposerEnabled,
    setSendButtonLoading,
    updateChatHeader,
    renderMessage,
    renderConversationHistory,
    renderAgentDropdown,
    createTypingIndicator,
    createTraceElement,
    renderCitations,
    scrollToBottom,
    clearChat,
    getAndClearInput
} from './ui/index.js';

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize the application
 */
async function init() {
    // Initialize DOM references
    initElements();

    // Show welcome screen
    showWelcomeScreen();
    setComposerEnabled(false);

    // Setup event listeners
    setupEventListeners();

    // Load initial data
    try {
        await Promise.all([
            loadConversations(),
            loadAgents()
        ]);
    } catch (err) {
        console.error("Failed to load initial data:", err);
    }
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Dropdown toggle
    elements.dropdownTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        elements.agentDropdown.classList.toggle("open");
    });

    // Close dropdowns and popups on outside click
    document.addEventListener("click", (e) => {
        if (!elements.agentDropdown.contains(e.target)) {
            elements.agentDropdown.classList.remove("open");
        }
        if (!e.target.closest(".history-item")) {
            document.querySelectorAll(".history-popup.show").forEach(p => p.classList.remove("show"));
            document.querySelectorAll(".menu-btn.active").forEach(b => b.classList.remove("active"));
        }
    });

    // New chat button
    elements.newChatBtn.addEventListener("click", handleNewChat);

    // Send message
    elements.sendBtn.addEventListener("click", handleSendMessage);
    elements.messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
}

// ============================================================================
// Data Loading
// ============================================================================

/**
 * Load and render agents
 */
async function loadAgents() {
    try {
        const agents = await fetchAgents();

        renderAgentDropdown(agents, (agentId) => {
            setCurrentAgent(agentId);
        });

        // Select first agent if current not found
        const hasCurrentAgent = agents.some(a => a.id === state.currentAgentId);
        if (!hasCurrentAgent && agents.length > 0) {
            setCurrentAgent(agents[0].id);
            elements.selectedAgentText.textContent = agents[0].name;
        }
    } catch (e) {
        console.error("Error fetching agents:", e);
    }
}

/**
 * Load and render conversations
 */
async function loadConversations() {
    try {
        const conversations = await fetchConversations();
        renderConversationHistory(
            conversations,
            handleSelectConversation,
            handleDeleteConversation
        );
    } catch (e) {
        console.error("Error fetching conversations:", e);
    }
}

// ============================================================================
// Event Handlers
// ============================================================================

/**
 * Handle new chat creation
 */
async function handleNewChat() {
    try {
        const conv = await apiCreateConversation("New Chat");
        await loadConversations();
        await handleSelectConversation(conv.id);
    } catch (err) {
        console.error("Error creating conversation:", err);
    }
}

/**
 * Handle conversation selection
 * @param {string} id - Conversation ID
 */
async function handleSelectConversation(id) {
    try {
        setCurrentConversation(id);
        await loadConversations(); // Update active state

        const data = await fetchConversation(id);

        clearChat();
        updateChatHeader(data.title || "Untitled Chat", data.id || id);
        setComposerEnabled(true);

        data.messages.forEach(msg => renderMessage(msg));
        scrollToBottom();
    } catch (err) {
        console.error("Error loading conversation:", err);
    }
}

/**
 * Handle conversation deletion
 * @param {string} id - Conversation ID
 */
async function handleDeleteConversation(id) {
    try {
        const success = await apiDeleteConversation(id);
        if (success) {
            if (state.currentConversationId === id) {
                setCurrentConversation(null);
                showWelcomeScreen();
                setComposerEnabled(false);
                updateChatHeader("New Chat");
            }
            await loadConversations();
        } else {
            console.error("Failed to delete conversation");
        }
    } catch (err) {
        console.error("Error deleting conversation:", err);
    }
}

/**
 * Handle sending a message
 */
async function handleSendMessage() {
    const text = getAndClearInput();
    if (!text || !state.currentConversationId || state.isProcessing) return;

    // Set loading state
    setSendButtonLoading(true);

    // Render user message
    renderMessage({ role: "user", content: text });

    // Prepare assistant message shell with typing indicator
    const { tracesDiv, bubble, citationsDiv } = renderMessage({
        role: "assistant",
        content: ""
    });
    const typingIndicator = createTypingIndicator();
    bubble.appendChild(typingIndicator);
    scrollToBottom();

    let fullAnswer = "";
    let firstChunk = true;

    try {
        const response = await apiSendMessage(
            state.currentConversationId,
            text,
            state.currentAgentId
        );

        await processStreamingResponse(response, (event) => {
            if (event.type === "answer") {
                // Remove typing indicator on first answer
                if (firstChunk) {
                    typingIndicator.remove();
                    firstChunk = false;
                }
                fullAnswer += event.content;
                bubble.innerHTML = marked.parse(fullAnswer);
            } else if (event.type === "citations") {
                renderCitations(event.citations || event.content, citationsDiv);
            } else {
                tracesDiv.appendChild(createTraceElement(event));
            }
    scrollToBottom();
        });

        // Remove typing indicator if no answer was received
        if (firstChunk && typingIndicator.parentNode) {
            typingIndicator.remove();
        }

        // Refresh conversation list for updated title
        setTimeout(loadConversations, 2000);

    } catch (err) {
        console.error("Chat error", err);
        typingIndicator.remove();
        bubble.textContent = "Error: " + err.message;
    } finally {
        setSendButtonLoading(false);
    }
}

// ============================================================================
// Start Application
// ============================================================================

init();
