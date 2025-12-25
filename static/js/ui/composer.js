/**
 * Composer Component
 * Handles the message input area and chat header
 */

import { elements, setProcessing } from '../state.js';

/**
 * Enable/disable the message composer
 * @param {boolean} enabled - Whether composer should be enabled
 */
export function setComposerEnabled(enabled) {
    elements.messageInput.disabled = !enabled;
    elements.sendBtn.disabled = !enabled;

    if (enabled) {
        elements.messageInput.placeholder = "Type a message to the agent...";
        elements.inputArea.style.opacity = "1";
        elements.inputArea.style.pointerEvents = "auto";
    } else {
        elements.messageInput.placeholder = "Select a chat or click \"+ New Chat\" to start...";
        elements.inputArea.style.opacity = "0.6";
        elements.inputArea.style.pointerEvents = "none";
    }
}

/**
 * Set send button loading state
 * @param {boolean} loading - Whether button is in loading state
 */
export function setSendButtonLoading(loading) {
    setProcessing(loading);
    if (loading) {
        elements.sendBtn.classList.add("loading");
        elements.sendBtn.disabled = true;
    } else {
        elements.sendBtn.classList.remove("loading");
        elements.sendBtn.disabled = false;
    }
}

/**
 * Update the chat header with title and ID
 * @param {string} title - Chat title
 * @param {string} id - Chat ID (optional)
 */
export function updateChatHeader(title, id = null) {
    elements.currentChatTitle.textContent = title;
    if (id) {
        elements.currentChatId.textContent = id;
        elements.currentChatId.style.display = "block";
    } else {
        elements.currentChatId.style.display = "none";
    }
}

/**
 * Get message input value and clear it
 * @returns {string} Trimmed input value
 */
export function getAndClearInput() {
    const text = elements.messageInput.value.trim();
    elements.messageInput.value = "";
    return text;
}

/**
 * Create typing indicator element
 * @returns {HTMLElement} Typing indicator DOM element
 */
export function createTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.id = "typing-indicator";
    indicator.innerHTML = `
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
    `;
    return indicator;
}
