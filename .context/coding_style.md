# Antigravity Coding Standards & Best Practices

*for Agentic IDEs & LLM-Driven Systems*

---

## 1. Architecture Principles

### 1.1 Tool Isolation (Hard Rule)

All external interactions **MUST** be encapsulated as tools inside the `tools/` directory.

**Includes:**

* API calls
* Database access
* File I/O
* System / shell commands
* Network requests

**Why?**

* Enables the agent to reason about capabilities as **discrete, callable actions**
* Prevents hidden side effects in core logic
* Makes tool usage auditable, testable, and replayable

✅ Good:

```python
tools/search_web.py
tools/read_file.py
tools/run_sql.py
```

❌ Bad:

```python
requests.get(...)  # inside agent loop
open("file.txt")   # inside planner
```

---

### 1.2 Strict Tool Boundaries

Tools:

* ❌ MUST NOT call other tools
* ❌ MUST NOT invoke the agent
* ❌ MUST NOT contain planning logic
* ✅ MUST perform exactly **one responsibility**

**Why?**
Tools are **actuators**, not thinkers.
Planning and orchestration belong to the agent loop.

---

### 1.3 Pydantic Everywhere (Schema-First Design)

Use **Pydantic models** for:

* Tool input arguments
* Tool return values
* Agent events
* Callback payloads

**Why?**

* Enforces strict schemas
* Makes tool contracts explicit
* Improves LLM reliability and grounding
* Enables automatic validation and introspection

```python
class SearchArgs(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
```

---

## 2. Python Style & Readability

### 2.1 Type Hints (Mandatory)

All public functions **MUST** have full type hints.

```python
def search_web(args: SearchArgs) -> SearchResult:
    ...
```

**Why?**
The agent uses type signatures to infer:

* Expected inputs
* Output structure
* Tool compatibility

---

### 2.2 Docstrings (Agent-Readable)

Google-style docstrings are **required** for all tools and agent-facing functions.

**Must include:**

* High-level description
* `Args`
* `Returns`
* `Raises` (if applicable)
* Optional **Usage Notes** (agent hints)

```python
def search_web(args: SearchArgs) -> SearchResult:
    """
    Searches the web for relevant documents.

    Args:
        args: Search parameters including query and result limit.

    Returns:
        A SearchResult object containing ranked documents.

    Raises:
        ToolExecutionError: If the search provider fails.

    Usage Notes:
        Best used for factual or up-to-date information.
    """
```

**Why?**
Docstrings are **part of the agent’s prompt**.

---

### 2.3 Naming Conventions

* Tools: `verb_noun` → `search_web`, `read_file`
* Pydantic models: `NounArgs`, `NounResult`
* Events: `AgentEvent`, `ToolEvent`, `ErrorEvent`

**Why?**
Consistent naming improves:

* Tool discoverability
* Autocompletion
* Prompt clarity

---

## 3. Agent Design Patterns

### 3.1 Stateless Tools (Default)

Tools should be **pure and stateless**.

Pass all required context explicitly:

* IDs
* Tokens
* File paths
* Configuration flags

```python
def fetch_user(user_id: str, auth_token: str) -> UserData:
    ...
```

**Why?**

* Enables safe retries
* Supports parallel execution
* Prevents hidden coupling

---

### 3.2 Fail Gracefully (Never Crash the Agent)

Tools **MUST NOT raise raw exceptions** to the agent loop.

Instead:

* Return structured error objects
* Or raise **domain-specific, catchable exceptions**

```python
class ToolError(BaseModel):
    code: str
    message: str
    recoverable: bool
```

**Why?**
Agents must be able to:

* Retry
* Switch strategy
* Ask the user for clarification

Crashes = dead agent.

---

### 3.3 Event-Driven Thinking

All meaningful actions should produce **AgentEvents**:

* Tool invoked
* Tool completed
* Tool failed
* Agent decision made

**Why?**

* Enables streaming UIs
* Debugging & replay
* Fine-grained callbacks
* Observability for reasoning traces

---

### 3.4 Deep Think Simulation (Explicit Reasoning)

For complex logic:

* Include **decision trees in comments**
* Or create a separate `DESIGN.md`

Example:

```python
# Decision Flow:
# 1. If user intent is unclear → ask clarification
# 2. If tool fails → retry once
# 3. If retry fails → fallback to summary-only response
```

**Why?**

* Makes reasoning auditable
* Helps future agents (and humans) modify behavior safely
* Avoids “magic” logic

---

## 4. Anti-Patterns (Explicitly Forbidden)

🚫 Hidden side effects
🚫 Tool calls inside tools
🚫 Silent exception swallowing
🚫 Dynamic dicts instead of schemas
🚫 Overloaded “do everything” tools
🚫 Business logic in callbacks

---

## 5. Core Philosophy

> **If the agent cannot see it, reason about it, or validate it — it doesn’t exist.**

Design for:

* Transparency
* Explicit contracts
* Recoverability
* Observability

This is not just clean code —
this is **code that thinks well with agents**.
