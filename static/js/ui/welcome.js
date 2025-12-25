/**
 * Welcome Screen Component
 * Displays the initial landing screen for new users
 */

import { elements } from '../state.js';

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
