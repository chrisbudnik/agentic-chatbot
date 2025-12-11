# Chatbot System Design Specification

## 1. System Architecture

The system follows a typical 3-tier web architecture with a focus on modularity to support AI agent extensibility.

### Components
1.  **Frontend (Client)**: 
    - Pure HTML/CSS/Vanilla JS. 
    - Served statically by the Backend.
    - Communicates via REST API (and optionally WebSocket) for chat interactions.
2.  **Backend (Server)**: 
    - **FastAPI** application acting as the orchestrator.
    - **Service Layer**: Decouples API routes from business logic (Agent processing).
    - **Agent Runtime**: Local module handling LLM interactions and tool execution.
3.  **Database**: 
    - **PostgreSQL**: Relational storage for structured data (conversations, tool logs).

### Directory Structure
```
custom-chatbot/
├── app/
│   ├── main.py              # Application entry point
│   ├── core/                # Core configurations (DB, Config, Logging)
│   ├── models/              # SQLAlchemy Database Models
│   ├── schemas/             # Pydantic Response/Request Models
│   ├── api/                 # API Route Handlers
│   │   ├── routers/
│   │   │   ├── conversations.py
│   │   │   ├── chat.py
│   │   │   ├── tools.py
│   │   │   └── admin.py
│   ├── services/            # Business Logic
│   │   ├── chat_service.py  # Orchestrates Message <-> Agent
│   │   └── agent_service.py # Agent Registry & Loading
│   ├── agents/              # Agent Implementations
│   │   ├── base.py          # Abstract Base Class
│   │   └── default_agent.py
│   └── tools/               # Tool Definitions
│       ├── base.py
│       ├── search_tool.py
│       └── db_tool.py
├── static/                  # Frontend Assets
│   ├── index.html
│   ├── js/
│   └── css/
├── alembic/                 # Migrations
├── requirements.txt
└── DESIGN.md
```

---

## 2. Database Schema (PostgreSQL)

We use SQLAlchemy ORM.

### Tables

**1. conversations**
- `id` (UUID, PK)
- `title` (String, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `status` (Enum: active, archived)

**2. messages**
- `id` (UUID, PK)
- `conversation_id` (UUID, FK -> conversations.id)
- `role` (Enum: user, assistant, system)
- `content` (Text)
- `created_at` (DateTime)
- `token_count` (Integer)
- `meta_data` (JSONB) - Stores model usage, latency.

**3. trace_logs** (The "Internal Thought" & "Tool" log)
- `id` (UUID, PK)
- `message_id` (UUID, FK -> messages.id) - The assistant message describing this step.
- `type` (Enum: thought, tool_call, tool_result, error)
- `content` (Text/JSON) - The reasoning text or tool args.
- `tool_name` (String, nullable)
- `timestamp` (DateTime)

**4. feedback**
- `id` (UUID, PK)
- `message_id` (UUID, FK -> messages.id)
- `rating` (Integer: -1 (down), 1 (up))
- `comment` (Text)
- `created_at` (DateTime)

**5. agents** (Registry for available agents)
- `id` (String, PK) - e.g., "finance_bot_v1"
- `name` (String)
- `description` (Text)
- `config` (JSONB) - Model name, temperature, specific tool permissions.

---

## 3. FastAPI Endpoints

### `/api/conversations`
- `POST /` - Create new conversation.
- `GET /` - List recent conversations.
- `GET /{id}` - Get full history.
- `DELETE /{id}` - Delete.

### `/api/chat`
- `POST /{conversation_id}/message` - Send user message. 
    - **Payload**: `{ "content": "Hello", "agent_id": "optional" }`
    - **Response**: Stream of events or final JSON object containing full response + steps.
- `POST /{conversation_id}/feedback/{message_id}` - Submit feedback.

### `/api/agents`
- `GET /` - List available agents.
- `GET /tools` - List available tools/schemas.

---

## 4. Frontend Structure

**Tech Stack**: Minimal HTML5, CSS3 (Variables for theming), ES6 Modules.

**Layout**:
- **Sidebar**: Conversation List, "New Chat" button.
- **Main Area**: Chat window.
    - **Message Stream**: Vertical scroll.
        - **User Bubble**: Right aligned.
        - **Assistant Bubble**: Left aligned. containing:
            - **Thought Accordion**: Collapsible details of "Reasoning".
            - **Tool Widget**: Visual block for "Calling WeatherTool...", "Result: 25c".
            - **Final Text**: The markdown response.
            - **Feedback Controls**: Tiny thumbs up/down icons.
    - **Input Area**: Textarea + Send Button + Attachment clip.

---

## 5. Agent & Tool Abstractions

### The Agent Interface (`app.agents.base.Agent`)
```python
class BaseAgent(ABC):
    def __init__(self, tools: List[BaseTool], model_config: dict):
        self.tools = tools
        self.client = ... # LLM Client initialization

    @abstractmethod
    async def process_turn(self, history: List[Message], user_input: str) -> AsyncIterator[AgentEvent]:
        """
        Generates a stream of events:
        - ReasoningStep(content="Thinking about X...")
        - ToolCallRequest(tool="Search", args={...})
        - ToolCallResult(output=...)
        - FinalAnswer(text="Here is the answer.")
        """
        pass
```

### The Tool Interface (`app.tools.base.Tool`)
```python
class BaseTool(ABC):
    name: str
    description: str
    input_schema: Type[PydanticModel]

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        pass
```

---

## 6. Data Flow (1 Turn)

1. **User** types message on Frontend -> hit `POST /chat/...`.
2. **Backend Router** delegates to `ChatService`.
3. `ChatService` saves User Message to DB.
4. `ChatService` loads the active `Agent` and calls `agent.process_turn`.
5. **Agent** sends prompts to LLM.
6. **Agent** yields `ReasoningStep` -> Service saves to `trace_logs` & streams to UI.
7. **Agent** decides to call Tool -> yields `ToolCallRequest`.
8. **Agent** executes Tool -> yields `ToolCallResult` -> Service saves result to `trace_logs`.
9. **Agent** incorporates tool result, re-prompts LLM.
10. **Agent** yields `FinalAnswer`.
11. `ChatService` saves Assistant Message to DB.
12. **Frontend** receives stream/response and renders the timeline.

## 7. Extensibility

- **New Agent**: Inherit from `BaseAgent`, implement specific prompting strategy (Sales vs Support), register in `agents/__init__.py`.
- **New Tool**: Inherit from `BaseTool`, define Pydantic schema, add to Agent allowed list.
- **New Frontend Feature**: Add vanilla JS module in `static/js/components/`.
