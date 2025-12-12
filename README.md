# Agentic Chatbot
![UI](images/ui-chat.png)

A production-ready, full-stack chatbot application featuring a **custom-built agentic AI framework**. This project demonstrates advanced patterns in AI engineering, including an event-driven "ReAct" (Reasoning + Acting) loop, real-time streaming of agent thoughts, and a modular architecture designed for extensibility.

## 🚀 Key Features

*   **Custom Agent Runtime**: A specialized Python framework that manages the LLM's lifecycle, handling the "Think → Tool Call → Result → Answer" loop autonomously.
*   **"Glass Box" AI UI**: Unlike standard chatbots, this frontend visualizes the agent's internal thought process. Users can expand the "Agent Process" accordion to see real-time reasoning, tool usage, and execution steps.
*   **Event-Driven Architecture**: The system uses a sophisticated callback & event system to stream granular updates (thoughts, citations, tool outputs) to the client via HTTP streaming.
*   **Tool Use & Citations**: Agents are equipped with tools (e.g., Search, Database) and can cite sources, which are parsed and displayed distinctly in the UI.
*   **Conversation Persistence**: Full history tracking with PostgreSQL, enabling long-running context-aware conversations.

## 🛠️ Architecture & Tech Stack

The application follows a clean 3-tier architecture, prioritizing separation of concerns and maintainability using **Python** and **Vanilla JS**.

### Backend (Python)
*   **FastAPI**: For high-performance, async API handling.
*   **SQLAlchemy (Async)**: ORM for robust database interactions with **PostgreSQL**.
*   **OpenAI API**: Powering the core reasoning engine.
*   **Custom Agent Service**: 
    *   `BaseAgent`: Abstract base defining the lifecycle.
    *   `LLMAgent`: Concrete implementation handling the ReAct loop and tool execution.
    *   `Callbacks`: Hooks (`before_agent_callback`, `after_agent_callback`) for modifying behavior on the fly.

### Frontend (Vanilla JS)
*   **Zero-Dependency Core**: Built with pure ES6 JavaScript, HTML5, and CSS3 for maximum performance and control.
*   **Streaming Logic**: Custom implementation of `ReadableStream` to handle complex, multi-type event streams from the backend.
*   **Dynamic Rendering**: Real-time DOM manipulation to render specific event types (e.g., rendering a JSON tool result differently from a text thought).

## 📂 Project Structure

```
├── app/
│   ├── agents/          # Custom Agent Framework (BaseAgent, LLMAgent)
│   ├── api/             # FastAPI Routers
│   ├── services/        # Business Logic & Orchestration
│   └── models/          # Database Models
├── static/              # Frontend (JS/CSS)
└── DESIGN.md            # Detailed Architecture Specification
```

## ⚡ Getting Started

This project uses `make` and `uv` for modern, fast Python management.

1.  **Install Dependencies**:
    ```bash
    make install
    ```

2.  **Configuration**:
    Create a `.env` file with your `OPENAI_API_KEY` and DATABASE_URL.

3.  **Run Development Server**:
    ```bash
    make dev
    ```
    The app will be available at `http://localhost:8000`.

## 🧠 Why This Custom Framework?
Instead of relying on heavy abstractions like LangChain for everything, this project implements the core agent loop from scratch. This approaches offers:
*   **Total Control**: Exact handling of prompts, context, and error states.
*   **Observability**: Granular logging and UI visualization of every step the agent takes.
*   **Performance**: Minimal overhead compared to larger libraries.
