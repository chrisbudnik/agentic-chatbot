/**
 * Sidebar Component
 * Handles conversation history and agent dropdown
 */

import { elements, state } from '../state.js';

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
