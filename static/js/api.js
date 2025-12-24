/**
 * API Service Module
 * Handles all communication with the backend
 */

import { API_BASE, state } from './state.js';

/**
 * Fetch available agents from the API
 * @returns {Promise<Array>} List of agents
 */
export async function fetchAgents() {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error("Failed to fetch agents");
    return res.json();
}

/**
 * Fetch all conversations
 * @returns {Promise<Array>} List of conversations
 */
export async function fetchConversations() {
    const res = await fetch(`${API_BASE}/conversations`);
    if (!res.ok) throw new Error("Failed to fetch conversations");
    return res.json();
}

/**
 * Fetch a single conversation by ID
 * @param {string} id - Conversation ID
 * @returns {Promise<Object>} Conversation data with messages
 */
export async function fetchConversation(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}`);
    if (!res.ok) throw new Error("Failed to fetch conversation");
    return res.json();
}

/**
 * Create a new conversation
 * @param {string} title - Conversation title
 * @returns {Promise<Object>} Created conversation
 */
export async function createConversation(title = "New Chat") {
    const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title })
    });
    if (!res.ok) throw new Error("Failed to create conversation");
    return res.json();
}

/**
 * Delete a conversation
 * @param {string} id - Conversation ID
 * @returns {Promise<boolean>} Success status
 */
export async function deleteConversation(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
        method: "DELETE"
    });
    return res.ok;
}

/**
 * Send a message to a conversation (streaming)
 * @param {string} conversationId - Conversation ID
 * @param {string} content - Message content
 * @param {string} agentId - Agent ID to use
 * @returns {Promise<Response>} Streaming response
 */
export async function sendMessage(conversationId, content, agentId) {
    const res = await fetch(`${API_BASE}/chat/${conversationId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, agent_id: agentId })
    });
    if (!res.ok) throw new Error("Failed to send message");
    return res;
}

/**
 * Process a streaming response
 * @param {Response} response - Fetch response with streaming body
 * @param {Function} onEvent - Callback for each parsed event
 */
export async function processStreamingResponse(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

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
                onEvent(event);
            } catch (e) {
                console.error("Parse error", e);
            }
        }
    }
}
