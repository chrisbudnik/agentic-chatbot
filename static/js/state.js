/**
 * Application State Management
 * Centralized state and DOM element references
 */

export const API_BASE = "/api";

// Application State
export const state = {
    currentConversationId: null,
    currentAgentId: "default",
    isProcessing: false
};

// DOM Element References (initialized after DOM loads)
export const elements = {
    historyList: null,
    chatContainer: null,
    messageInput: null,
    sendBtn: null,
    newChatBtn: null,
    agentDropdown: null,
    dropdownTrigger: null,
    dropdownMenu: null,
    selectedAgentText: null,
    currentChatTitle: null,
    currentChatId: null,
    inputArea: null
};

/**
 * Initialize DOM element references
 * Call this after DOM is ready
 */
export function initElements() {
    elements.historyList = document.getElementById("history-list");
    elements.chatContainer = document.getElementById("chat-container");
    elements.messageInput = document.getElementById("message-input");
    elements.sendBtn = document.getElementById("send-btn");
    elements.newChatBtn = document.getElementById("new-chat-btn");
    elements.agentDropdown = document.getElementById("agent-dropdown");
    elements.dropdownTrigger = document.getElementById("dropdown-trigger");
    elements.dropdownMenu = document.getElementById("dropdown-menu");
    elements.selectedAgentText = document.getElementById("selected-agent-text");
    elements.currentChatTitle = document.getElementById("current-chat-title");
    elements.currentChatId = document.getElementById("current-chat-id");
    elements.inputArea = document.getElementById("input-area");
}

/**
 * Update conversation ID
 */
export function setCurrentConversation(id) {
    state.currentConversationId = id;
}

/**
 * Update current agent
 */
export function setCurrentAgent(id) {
    state.currentAgentId = id;
}

/**
 * Update processing state
 */
export function setProcessing(processing) {
    state.isProcessing = processing;
}
