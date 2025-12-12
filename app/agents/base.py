from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Optional
from pydantic import BaseModel
import asyncio
import inspect
import json

from app.tools.base import BaseTool


# ============================================================
# EVENT MODEL
# ============================================================

class AgentEvent(BaseModel):
    type: str  # thought, tool_call, tool_result, answer, error
    content: str
    tool_name: str = None
    tool_args: dict = None
    tool_call_id: str = None
    callback_type: str = None


# ============================================================
# COLLECTOR
# ============================================================

class CallbackCollector:
    """Stores final result of each callback."""
    def __init__(self):
        self.before_modified_input: Optional[str] = None
        self.after_events: List[AgentEvent] = []


# ============================================================
# BASE AGENT
# ============================================================

class BaseAgent(ABC):
    def __init__(
        self,
        tools: List[BaseTool] = [],
        name: str = "Agent",
        description: str = "",
        system_prompt: str = "You are a helpful assistant.",
        model: str = "gpt-4.1",
        before_agent_callback=None,
        after_agent_callback=None
    ) -> None:

        self.tools = {t.name: t for t in tools}
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.model = model

        self.before_agent_callback = before_agent_callback
        self.after_agent_callback = after_agent_callback


    # ============================================================
    # INTERNAL UNIFIED CALLBACK HANDLER
    # ============================================================

    async def _run_callback_with_events(
        self,
        callback_fn,
        callback_input,
        collector: CallbackCollector,
        collector_attr: str,   # e.g., "before_modified_input" or "after_events"
        callback_type: str
    ) -> AsyncIterator[AgentEvent]:
        """
        Runs a callback function and returns an async iterator of events.

        Callbacks can return varied object types:
        - async generator of events
        - list of events
        - single event
        - simple value (before-callback case)

        if callback returns a value, it is stored in the collector.
        else we emit events as we go.
        
        Args:
            callback_fn: The callback function to run.
            callback_input: The input to the callback function.
            collector: The collector to use.
            collector_attr: The attribute of the collector to use.
            callback_type: The type of the callback.
        """
        if callback_fn is None:
            return

        yield AgentEvent(
            type="execute_callback",
            content=f"Running {callback_type}",
            callback_type=callback_type
        )

        try:
            # Run callback — may return:
            #  - async generator of events
            #  - list of events
            #  - single event
            #  - simple value (before-callback case)
            result = callback_fn(callback_input)

            # Case 1 — streaming callback
            if inspect.isasyncgen(result):
                async for event in result:
                    yield event
                setattr(collector, collector_attr, None)  # no “value result”

            else:
                # Normal async return
                result = await result

                # Case 2 — value (e.g., modified_input)
                if isinstance(result, str) and collector_attr == "before_modified_input":
                    collector.before_modified_input = result
                    yield AgentEvent(
                        type="execute_callback_result",
                        content=f"Modified user input: {result}",
                        callback_type=callback_type
                    )

                # Case 3 — event
                elif isinstance(result, AgentEvent):
                    getattr(collector, collector_attr).append(result)
                    yield result

                # Case 4 — list of events
                elif isinstance(result, list):
                    for ev in result:
                        if isinstance(ev, AgentEvent):
                            getattr(collector, collector_attr).append(ev)
                            yield ev

                # Case 5 — fallback
                else:
                    yield AgentEvent(
                        type="callback_unrecognized_output",
                        content=f"Callback returned unknown type: {type(result)}",
                        callback_type=callback_type
                    )

        except Exception as e:
            yield AgentEvent(
                type="error",
                content=f"{type(e).__name__}: {e}",
                callback_type=callback_type
            )


    # ============================================================
    # BEFORE CALLBACK
    # ============================================================

    async def process_before_agent_callback(
        self, user_input: str, history: List[dict], collector: CallbackCollector
    ) -> AsyncIterator[AgentEvent]:

        if not self.before_agent_callback:
            collector.before_modified_input = user_input
            return

        async for event in self._run_callback_with_events(
            callback_fn=self.before_agent_callback,
            callback_input=(user_input, history),
            collector=collector,
            collector_attr="before_modified_input",
            callback_type="before_agent_callback"
        ):
            yield event

        # If callback produced no new user input, fallback
        if collector.before_modified_input is None:
            collector.before_modified_input = user_input


    # ============================================================
    # AFTER CALLBACK
    # ============================================================

    async def process_after_agent_callback(
        self, final_answer: AgentEvent, collector: CallbackCollector
    ) -> AsyncIterator[AgentEvent]:

        if not self.after_agent_callback:
            yield final_answer
            return

        async for event in self._run_callback_with_events(
            callback_fn=self.after_agent_callback,
            callback_input=final_answer,
            collector=collector,
            collector_attr="after_events",
            callback_type="after_agent_callback"
        ):
            yield event


    # ============================================================
    # MAIN TURN PROCESSOR
    # ============================================================

    async def process_turn(
        self, history: List[dict], user_input: str
    ) -> AsyncIterator[AgentEvent]:

        collector = CallbackCollector()

        # BEFORE CALLBACK
        async for event in self.process_before_agent_callback(user_input, history, collector):
            yield event

        # MAIN AGENT LOGIC
        final_answer_event = None
        async for event in self._process_turn(history, collector.before_modified_input):
            if event.type == "answer":
                final_answer_event = event
            yield event

        # AFTER CALLBACK
        if final_answer_event:
            async for event in self.process_after_agent_callback(final_answer_event, collector):
                yield event


    # ============================================================
    # ABSTRACT MAIN STEP
    # ============================================================

    @abstractmethod
    async def _process_turn(self, history: List[dict], user_input: str) -> AsyncIterator[AgentEvent]:
        """
        Abstract method to process a turn. Implemented by subclasses.
        """
        pass

