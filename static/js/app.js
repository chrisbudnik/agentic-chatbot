const API_BASE = "/api";

let currentConversationId = null;

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
let currentAgentId = "default";

// Init
async function init() {
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
        selectedAgentText.textContent = item.textContent;

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
    sendBtn.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Load Data
    try {
        await loadConversations();
    } catch (err) {
        console.error("Failed to load conversations:", err);
    }

    // Load first conv if exists? Or just wait.
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
                chatContainer.innerHTML = `
                    <div style="text-align:center; color: #8b949e; margin-top: 2rem;">
                        <h2>Welcome to Agent Chat</h2>
                        <p>Select a conversation or start a new one.</p>
                    </div>`;
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
                renderCitations(t.content, citationsDiv);
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
        if (!citations || !Array.isArray(citations) || citations.length === 0) return;

        container.innerHTML = ""; // Clear existing
        const title = document.createElement("div");
        title.className = "citations-title";
        title.textContent = "Sources:";
        container.appendChild(title);

        const list = document.createElement("ul");
        citations.forEach(c => {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = c.url;
            a.textContent = c.title || c.url;
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            li.appendChild(a);
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
    if (!text || !currentConversationId) return;

    // UI: Clear input & Show User Message
    messageInput.value = "";
    renderFullMessage({ role: "user", content: text });

    // UI: Prepare Assistant Shell
    const { tracesDiv, bubble, citationsDiv } = renderFullMessage({ role: "assistant", content: "" });
    bubble.textContent = ""; // Waiting...
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

        // Refresh conversation list to show updated title (if generated)
        setTimeout(loadConversations, 2000);

    } catch (err) {
        console.error("Chat error", err);
        bubble.textContent = "Error: " + err.message;
    }
}

function handleStreamEvent(event, tracesDiv, bubble, citationsDiv) {
    if (event.type === "citations") {
        renderCitations(event.content, citationsDiv);
    } else {
        const el = createTraceElement(event);
        tracesDiv.appendChild(el);
    }
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

init();
