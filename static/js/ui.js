/**
 * UI Rendering Module
 * Handles all UI rendering and DOM manipulation
 */

import { elements, state, setProcessing } from './state.js';

// ============================================================================
// Welcome Screen
// ============================================================================

/**
 * Generate welcome screen HTML
 * @returns {string} Welcome screen HTML
 */
export function renderWelcomeScreen() {
    return `
        <div id="welcome-screen" class="welcome-screen">
            <h1 class="welcome-title">Agentic Chat</h1>
            <div class="welcome-content">
                <p class="welcome-subtitle">Explore the capabilities of autonomous AI agents.</p>
                <ul class="welcome-features">
                    <li class="welcome-feature">
                        <span class="welcome-feature-icon">🤖</span>
                        <div>
                            <strong class="welcome-feature-title">Multi-Model Agents</strong>
                            <span class="welcome-feature-desc">Switch between different specialized agents for various tasks.</span>
                        </div>
                    </li>
                    <li class="welcome-feature">
                        <span class="welcome-feature-icon">🛠️</span>
                        <div>
                            <strong class="welcome-feature-title">Tool Integration</strong>
                            <span class="welcome-feature-desc">Agents can use tools to fetch data and perform actions.</span>
                        </div>
                    </li>
                    <li class="welcome-feature">
                        <span class="welcome-feature-icon">🔄</span>
                        <div>
                            <strong class="welcome-feature-title">Event Callbacks</strong>
                            <span class="welcome-feature-desc">Hook into the agent lifecycle to monitor execution and trigger side-effects.</span>
                        </div>
                    </li>
                    <li class="welcome-feature">
                        <span class="welcome-feature-icon">🧠</span>
                        <div>
                            <strong class="welcome-feature-title">Transparent Workflows</strong>
                            <span class="welcome-feature-desc">View the agent's internal thoughts and execution steps in real-time.</span>
                        </div>
                    </li>
                </ul>
                <div class="welcome-cta">
                    <span>To get started, click <strong>+ New Chat</strong> in the sidebar.</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Show welcome screen in chat container
 */
export function showWelcomeScreen() {
    elements.chatContainer.innerHTML = renderWelcomeScreen();
}

// ============================================================================
// Typing Indicator
// ============================================================================

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

// ============================================================================
// Composer State
// ============================================================================

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

// ============================================================================
// Chat Header
// ============================================================================

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

// ============================================================================
// Message Rendering
// ============================================================================

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

// ============================================================================
// Trace Elements
// ============================================================================

/**
 * Create a trace element for the agent process log
 * @param {Object} traceObj - Trace object with type and content
 * @returns {HTMLElement} Trace DOM element
 */
export function createTraceElement(traceObj) {
    const el = document.createElement("div");
    el.className = `trace-item ${traceObj.type}`;

    const header = document.createElement("div");
    header.className = "trace-header";

    const details = document.createElement("div");
    details.className = "trace-details";
    details.style.display = "none";

    let label = "";
    let detailContent = "";

    switch (traceObj.type) {
        case "thought":
            label = "🤔 Thought";
            detailContent = traceObj.content;
            break;
        case "tool_call":
            label = `🔧 Calling ${traceObj.tool_name}...`;
            detailContent = JSON.stringify(traceObj.tool_args || {}, null, 2);
            break;
        case "tool_result":
            const preview = traceObj.content.length > 50
                ? traceObj.content.substring(0, 50) + "..."
                : traceObj.content;
            label = `✅ Result: ${preview}`;
            detailContent = traceObj.content;
            break;
        case "execute_callback":
            const cbType = traceObj.callback_type ? ` (${traceObj.callback_type})` : "";
            label = `🔄 Executing Callback${cbType}`;
            detailContent = traceObj.content;
            break;
        case "execute_callback_result":
            label = "✅ Callback Result";
            detailContent = traceObj.content;
            break;
        case "error":
            label = "❌ Error";
            detailContent = traceObj.content;
            break;
        default:
            label = traceObj.content;
            detailContent = traceObj.content;
    }

    header.textContent = label;
    details.textContent = detailContent;

    header.onclick = () => {
        const isHidden = details.style.display === "none";
        details.style.display = isHidden ? "block" : "none";
        header.classList.toggle("expanded", isHidden);
    };

    el.appendChild(header);
    el.appendChild(details);
    return el;
}

// ============================================================================
// Citations
// ============================================================================

/**
 * Render citations in a container
 * @param {string|Array|Object} content - Citations data
 * @param {HTMLElement} container - Container element
 */
export function renderCitations(content, container) {
    try {
        const citations = typeof content === 'string' ? JSON.parse(content) : content;

        let citationList = [];
        if (Array.isArray(citations)) {
            citationList = citations.map(c => {
                if (typeof c === 'string') return { title: c, url: c };
                return {
                    title: c.title || c.url,
                    url: c.url,
                    page_span_start: c.page_span_start,
                    page_span_end: c.page_span_end,
                };
            });
        } else if (citations && typeof citations === 'object') {
            citationList = Object.entries(citations).map(([name, url]) => ({
                title: name,
                url: url
            }));
        }

        if (citationList.length === 0) return;

        container.innerHTML = "";

        const title = document.createElement("div");
        title.className = "citations-title";
        title.textContent = "Sources:";
        container.appendChild(title);

        const list = document.createElement("ul");
        citationList.forEach(c => {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = c.url;
            a.textContent = c.title;
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            li.appendChild(a);

            const pageRange = formatPageRange(c);
            if (pageRange) {
                const meta = document.createElement("span");
                meta.className = "citation-page-range";
                meta.textContent = pageRange;
                li.appendChild(meta);
            }
            list.appendChild(li);
        });

        container.appendChild(list);
        container.style.display = "block";
    } catch (e) {
        console.error("Failed to parse citations", e);
    }
}

/**
 * Format page range for citation
 * @param {Object} citation - Citation object with page_span_start/end
 * @returns {string} Formatted page range
 */
function formatPageRange(c) {
    const start = c?.page_span_start;
    const end = c?.page_span_end;

    if (typeof start !== "number" && typeof end !== "number") return "";
    if (typeof start === "number" && typeof end === "number") {
        if (start === end) return `p. ${start}`;
        return `pp. ${start}–${end}`;
    }
    const single = (typeof start === "number") ? start : end;
    return `p. ${single}`;
}

// ============================================================================
// Conversation History
// ============================================================================

/**
 * Render conversation history in sidebar
 * @param {Array} conversations - List of conversations
 * @param {Function} onSelect - Callback when conversation is selected
 * @param {Function} onDelete - Callback when conversation is deleted
 */
export function renderConversationHistory(conversations, onSelect, onDelete) {
    elements.historyList.innerHTML = "";

    conversations.forEach(conv => {
        const el = document.createElement("div");
        el.className = `history-item ${state.currentConversationId === conv.id ? 'active' : ''}`;

        // Title
        const titleSpan = document.createElement("span");
        titleSpan.className = "history-title";
        titleSpan.textContent = conv.title || "Untitled Chat";
        el.appendChild(titleSpan);

        // Menu Button
        const menuBtn = document.createElement("button");
        menuBtn.className = "menu-btn";
        menuBtn.innerHTML = "⋯";
        menuBtn.title = "Options";

        // Popup Menu
        const popup = document.createElement("div");
        popup.className = "history-popup";

        const deleteItem = document.createElement("div");
        deleteItem.className = "history-popup-item";
        deleteItem.innerHTML = "Delete";
        deleteItem.onclick = (e) => {
            e.stopPropagation();
            if (confirm("Delete this conversation?")) {
                onDelete(conv.id);
            }
            popup.classList.remove("show");
        };

        popup.appendChild(deleteItem);
        el.appendChild(popup);

        menuBtn.onclick = (e) => {
            e.stopPropagation();
            // Close other popups
            document.querySelectorAll(".history-popup.show").forEach(p => {
                if (p !== popup) p.classList.remove("show");
            });
            document.querySelectorAll(".menu-btn.active").forEach(b => {
                if (b !== menuBtn) b.classList.remove("active");
            });
            menuBtn.classList.toggle("active");
            popup.classList.toggle("show");
        };

        el.appendChild(menuBtn);
        el.onclick = () => onSelect(conv.id);
        elements.historyList.appendChild(el);
    });
}

// ============================================================================
// Agent Dropdown
// ============================================================================

/**
 * Render agents in dropdown menu
 * @param {Array} agents - List of agents
 * @param {Function} onSelect - Callback when agent is selected
 */
export function renderAgentDropdown(agents, onSelect) {
    elements.dropdownMenu.innerHTML = "";

    agents.forEach(agent => {
        const div = document.createElement("div");
        div.className = "dropdown-item";
        div.dataset.value = agent.id;

        const nameSpan = document.createElement("span");
        nameSpan.className = "dropdown-item-name";
        nameSpan.textContent = agent.name;
        div.appendChild(nameSpan);

        if (agent.description) {
            const descSpan = document.createElement("span");
            descSpan.className = "dropdown-item-desc";
            descSpan.textContent = agent.description;
            div.appendChild(descSpan);
        }

        if (agent.id === state.currentAgentId) {
            div.classList.add("selected");
            elements.selectedAgentText.textContent = agent.name;
        }

        div.onclick = () => {
            document.querySelectorAll(".dropdown-item").forEach(el => el.classList.remove("selected"));
            div.classList.add("selected");
            elements.selectedAgentText.textContent = agent.name;
            elements.agentDropdown.classList.remove("open");
            onSelect(agent.id);
        };

        elements.dropdownMenu.appendChild(div);
    });
}

// ============================================================================
// Utility Functions
// ============================================================================

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

/**
 * Get message input value and clear it
 * @returns {string} Trimmed input value
 */
export function getAndClearInput() {
    const text = elements.messageInput.value.trim();
    elements.messageInput.value = "";
    return text;
}
