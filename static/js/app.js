const API_BASE = "/api";

let currentConversationId = null;
let isProcessing = false;

// DOM Elements
const historyList = document.getElementById("history-list");
const chatContainer = document.getElementById("chat-container");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
// Custom Dropdown Elements
const agentDropdown = document.getElementById("agent-dropdown");
const dropdownTrigger = document.getElementById("dropdown-trigger");
const dropdownMenu = document.getElementById("dropdown-menu");
const selectedAgentText = document.getElementById("selected-agent-text");
const currentChatTitle = document.getElementById("current-chat-title");
const inputArea = document.getElementById("input-area");
let currentAgentId = "default";

// Welcome Screen Template
function renderWelcomeScreen() {
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

// Typing Indicator
function createTypingIndicator() {
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

// Send Button State Management
function setSendButtonLoading(loading) {
    isProcessing = loading;
    if (loading) {
        sendBtn.classList.add("loading");
        sendBtn.disabled = true;
    } else {
        sendBtn.classList.remove("loading");
        sendBtn.disabled = false;
    }
}

function setComposerEnabled(enabled) {
    // Keep the composer visible at all times; just enable/disable it.
    messageInput.disabled = !enabled;
    sendBtn.disabled = !enabled;

    if (enabled) {
        messageInput.placeholder = "Type a message to the agent...";
        inputArea.style.opacity = "1";
        inputArea.style.pointerEvents = "auto";
    } else {
        messageInput.placeholder = "Select a chat or click “+ New Chat” to start...";
        inputArea.style.opacity = "0.6";
        inputArea.style.pointerEvents = "none";
    }
}

// Init
async function init() {
    // Render welcome screen on load
    chatContainer.innerHTML = renderWelcomeScreen();
    setComposerEnabled(false);

    // Dropdown Logic (Attach immediately)
    dropdownTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        agentDropdown.classList.toggle("open");
    });

    dropdownMenu.addEventListener("click", (e) => {
        const item = e.target.closest(".dropdown-item");
        if (!item) return;

        // Update State
        currentAgentId = item.dataset.value;
        const nameSpan = item.querySelector(".dropdown-item-name");
        selectedAgentText.textContent = nameSpan ? nameSpan.textContent : item.textContent;

        // Update UI
        document.querySelectorAll(".dropdown-item").forEach(el => el.classList.remove("selected"));
        item.classList.add("selected");

        // Close
        agentDropdown.classList.remove("open");
    });

    // Close on click outside
    // Close on click outside
    document.addEventListener("click", (e) => {
        if (!agentDropdown.contains(e.target)) {
            agentDropdown.classList.remove("open");
        }

        // Close history popups
        if (!e.target.closest(".history-item")) {
            document.querySelectorAll(".history-popup.show").forEach(p => p.classList.remove("show"));
            document.querySelectorAll(".menu-btn.active").forEach(b => b.classList.remove("active"));
        }
    });

    // Listeners
    newChatBtn.addEventListener("click", createConversation);
    // document.addEventListener("click", (e) => { ... }); Removed center button listener

    sendBtn.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Load Data
    try {
        await Promise.all([loadConversations(), fetchAgents()]);
    } catch (err) {
        console.error("Failed to load initial data:", err);
    }
}

async function fetchAgents() {
    try {
        const res = await fetch(`${API_BASE}/agents`);
        if (!res.ok) throw new Error("Failed to fetch agents");
        const agents = await res.json();

        const menu = document.getElementById("dropdown-menu");
        menu.innerHTML = "";

        let foundCurrent = false;

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

            if (agent.id === currentAgentId) {
                div.classList.add("selected");
                selectedAgentText.textContent = agent.name;
                foundCurrent = true;
            }
            menu.appendChild(div);
        });

        // If current default is not found, select the first one
        if (!foundCurrent && agents.length > 0) {
            currentAgentId = agents[0].id;
            selectedAgentText.textContent = agents[0].name;
            menu.firstElementChild.classList.add("selected");
        }

    } catch (e) {
        console.error("Error fetching agents:", e);
    }
}

async function loadConversations() {
    const res = await fetch(`${API_BASE}/conversations`);
    const convs = await res.json();
    historyList.innerHTML = "";
    convs.forEach(c => {
        const el = document.createElement("div");
        el.className = `history-item ${currentConversationId === c.id ? 'active' : ''}`;

        const titleSpan = document.createElement("span");
        titleSpan.className = "history-title";
        titleSpan.textContent = c.title || "Untitled Chat";
        el.appendChild(titleSpan);

        // Menu Button (Three dots)
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
                deleteConversation(c.id);
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

        // Click on item loads conversation
        el.onclick = () => loadConversation(c.id);

        historyList.appendChild(el);
    });

    // Close popups on click outside (using a global listener attached once or handled here)
    // We already have a global click listener for agent dropdown. Let's add one generic closer in init.
}

async function deleteConversation(id) {
    try {
        const res = await fetch(`${API_BASE}/conversations/${id}`, {
            method: "DELETE"
        });
        if (res.ok) {
            // content cleared
            if (currentConversationId === id) {
                currentConversationId = null;
                chatContainer.innerHTML = renderWelcomeScreen();
                setComposerEnabled(false);
                document.getElementById("current-chat-title").textContent = "New Chat";
                document.getElementById("current-chat-id").style.display = "none";
            }
            loadConversations();
        } else {
            console.error("Failed to delete conversation");
        }
    } catch (err) {
        console.error("Error deleting conversation:", err);
    }
}

async function createConversation() {
    const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Chat" })
    });
    const conv = await res.json();
    await loadConversations();
    loadConversation(conv.id);
    currentChatTitle.textContent = "New Chat";
    const idDisplay = document.getElementById("current-chat-id");
    idDisplay.textContent = conv.id;
    idDisplay.style.display = "block";
    setComposerEnabled(true);
}

async function loadConversation(id) {
    currentConversationId = id;
    loadConversations(); // update active state

    const res = await fetch(`${API_BASE}/conversations/${id}`);
    const data = await res.json();

    chatContainer.innerHTML = "";
    currentChatTitle.textContent = data.title || "Untitled Chat";
    const idDisplay = document.getElementById("current-chat-id");
    idDisplay.textContent = data.id || id;
    idDisplay.style.display = "block";
    setComposerEnabled(true);
    data.messages.forEach(renderFullMessage);
    scrollToBottom();
}

function renderFullMessage(msg) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${msg.role}`;

    let tracesDiv = null;

    if (msg.role === "assistant") {
        // Create collapsible container for Agent Process
        const processWrapper = document.createElement("div");
        processWrapper.className = "process-wrapper open"; // Default to expanded
        // User can click header to toggle.

        const processHeader = document.createElement("div");
        processHeader.className = "process-header";
        processHeader.textContent = "Agent Process";

        processHeader.onclick = () => {
            processWrapper.classList.toggle("open");
        };

        tracesDiv = document.createElement("div");
        tracesDiv.className = "trace-log";

        processWrapper.appendChild(processHeader);
        processWrapper.appendChild(tracesDiv);
        msgDiv.appendChild(processWrapper);
    } else {
        // User messages usually don't have traces, but keep structure valid just in case
        tracesDiv = document.createElement("div");
        tracesDiv.className = "trace-log";
        tracesDiv.style.display = "none"; // Hide standard container for user
        msgDiv.appendChild(tracesDiv);
    }



    // 2. Render Content
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = marked.parse(msg.content || "");
    msgDiv.appendChild(bubble);

    // 3. Citations
    const citationsDiv = document.createElement("div");
    citationsDiv.className = "citations";
    citationsDiv.style.display = "none";
    msgDiv.appendChild(citationsDiv);

    if (msg.traces && msg.traces.length > 0) {
        msg.traces.forEach(t => {
            if (t.type === "citations") {
                renderCitations(t.citations || t.content, citationsDiv);
            } else {
                const tEl = createTraceElement(t);
                tracesDiv.appendChild(tEl);
            }
        });
    }

    if (msg.citations) {
        renderCitations(msg.citations, citationsDiv);
    }

    chatContainer.appendChild(msgDiv);
    return { msgDiv, tracesDiv, bubble, citationsDiv };
}

function renderCitations(content, container) {
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
            citationList = Object.entries(citations).map(([name, url]) => ({ title: name, url: url }));
        }

        if (citationList.length === 0) return;

        const formatPageRange = (c) => {
            const start = c?.page_span_start;
            const end = c?.page_span_end;

            if (typeof start !== "number" && typeof end !== "number") return "";
            if (typeof start === "number" && typeof end === "number") {
                if (start === end) return `p. ${start}`;
                return `pp. ${start}\u2013${end}`;
            }
            const single = (typeof start === "number") ? start : end;
            return `p. ${single}`;
        };

        container.innerHTML = ""; // Clear existing
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

function createTraceElement(traceObj) {
    const el = document.createElement("div");
    el.className = `trace-item ${traceObj.type}`;

    // Header
    const header = document.createElement("div");
    header.className = "trace-header";

    // Details
    const details = document.createElement("div");
    details.className = "trace-details";
    details.style.display = "none"; // Start collapsed

    let label = "";
    let detailContent = "";

    if (traceObj.type === "thought") {
        label = `🤔 Thought`;
        detailContent = traceObj.content;
    } else if (traceObj.type === "tool_call") {
        label = `🔧 Calling ${traceObj.tool_name}...`;
        detailContent = JSON.stringify(traceObj.tool_args || {}, null, 2);
    } else if (traceObj.type === "tool_result") {
        const preview = traceObj.content.length > 50 ? traceObj.content.substring(0, 50) + "..." : traceObj.content;
        label = `✅ Result: ${preview}`;
        detailContent = traceObj.content;
    } else if (traceObj.type === "execute_callback") {
        const cbType = traceObj.callback_type ? ` (${traceObj.callback_type})` : "";
        label = `🔄 Executing Callback${cbType}`;
        detailContent = traceObj.content;
    } else if (traceObj.type === "execute_callback_result") {
        label = `✅ Callback Result`;
        detailContent = traceObj.content;
    } else if (traceObj.type === "error") {
        label = `❌ Error`;
        detailContent = traceObj.content;
    } else {
        label = traceObj.content;
        detailContent = traceObj.content;
    }

    header.textContent = label;
    details.textContent = detailContent;

    header.onclick = () => {
        const isHidden = details.style.display === "none";
        details.style.display = isHidden ? "block" : "none";
        if (isHidden) header.classList.add("expanded");
        else header.classList.remove("expanded");
    };

    el.appendChild(header);
    el.appendChild(details);
    return el;
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || !currentConversationId || isProcessing) return;

    // UI: Set loading state
    setSendButtonLoading(true);
    messageInput.value = "";

    // UI: Show User Message
    renderFullMessage({ role: "user", content: text });

    // UI: Prepare Assistant Shell with typing indicator
    const { tracesDiv, bubble, citationsDiv } = renderFullMessage({ role: "assistant", content: "" });
    const typingIndicator = createTypingIndicator();
    bubble.appendChild(typingIndicator);
    scrollToBottom();

    try {
        const response = await fetch(`${API_BASE}/chat/${currentConversationId}/message`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: text, agent_id: currentAgentId })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullAnswer = "";
        let firstChunk = true;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // Keep incomplete line

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const event = JSON.parse(line);
                    if (event.type === "answer") {
                        // Remove typing indicator on first answer chunk
                        if (firstChunk) {
                            typingIndicator.remove();
                            firstChunk = false;
                        }
                        fullAnswer += event.content;
                        bubble.innerHTML = marked.parse(fullAnswer);
                    } else {
                        handleStreamEvent(event, tracesDiv, bubble, citationsDiv);
                    }
                    scrollToBottom();
                } catch (e) {
                    console.error("Parse error", e);
                }
            }
        }

        // Remove typing indicator if still present (no answer received)
        if (firstChunk && typingIndicator.parentNode) {
            typingIndicator.remove();
        }

        // Refresh conversation list to show updated title (if generated)
        setTimeout(loadConversations, 2000);

    } catch (err) {
        console.error("Chat error", err);
        typingIndicator.remove();
        bubble.textContent = "Error: " + err.message;
    } finally {
        setSendButtonLoading(false);
    }
}

function handleStreamEvent(event, tracesDiv, bubble, citationsDiv) {
    if (event.type === "citations") {
        renderCitations(event.citations || event.content, citationsDiv);
    } else {
        const el = createTraceElement(event);
        tracesDiv.appendChild(el);
    }
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

init();
