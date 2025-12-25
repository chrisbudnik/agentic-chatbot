/**
 * Messages Component
 * Handles rendering of chat messages
 */

import { elements } from '../state.js';
import { createTraceElement } from './traces.js';
import { renderCitations } from './citations.js';

/**
 * Render a complete message (user or assistant)
 * @param {Object} msg - Message object with role, content, traces, citations
 * @returns {Object} References to created DOM elements
 */
export function renderMessage(msg) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${msg.role}`;

    let tracesDiv = null;

    if (msg.role === "assistant") {
        // Create collapsible container for Agent Process
        const processWrapper = document.createElement("div");
        processWrapper.className = "process-wrapper open";

        const processHeader = document.createElement("div");
        processHeader.className = "process-header";
        processHeader.textContent = "Agent Process";
        processHeader.onclick = () => processWrapper.classList.toggle("open");

        tracesDiv = document.createElement("div");
        tracesDiv.className = "trace-log";

        processWrapper.appendChild(processHeader);
        processWrapper.appendChild(tracesDiv);
        msgDiv.appendChild(processWrapper);
    } else {
        // User messages - hidden trace container
        tracesDiv = document.createElement("div");
        tracesDiv.className = "trace-log";
        tracesDiv.style.display = "none";
        msgDiv.appendChild(tracesDiv);
    }

    // Content bubble
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = marked.parse(msg.content || "");
    msgDiv.appendChild(bubble);

    // Citations container
    const citationsDiv = document.createElement("div");
    citationsDiv.className = "citations";
    citationsDiv.style.display = "none";
    msgDiv.appendChild(citationsDiv);

    // Render existing traces
    if (msg.traces && msg.traces.length > 0) {
        msg.traces.forEach(t => {
            if (t.type === "citations") {
                renderCitations(t.citations || t.content, citationsDiv);
            } else {
                tracesDiv.appendChild(createTraceElement(t));
            }
        });
    }

    // Render existing citations
    if (msg.citations) {
        renderCitations(msg.citations, citationsDiv);
    }

    elements.chatContainer.appendChild(msgDiv);
    return { msgDiv, tracesDiv, bubble, citationsDiv };
}

/**
 * Scroll chat container to bottom
 */
export function scrollToBottom() {
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

/**
 * Clear chat container
 */
export function clearChat() {
    elements.chatContainer.innerHTML = "";
}
