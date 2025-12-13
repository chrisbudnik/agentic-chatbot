from typing import AsyncIterator, List, Optional
import inspect
from app.agents.models import AgentEvent, CallbackContext



async def run_callback_with_events(
    callback_fn,
    callback_input,
    context: CallbackContext,
    context_attr: str,
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
        result = callback_fn(**callback_input)

        # Case 1 — streaming callback (async gen)
        if inspect.isasyncgen(result):
            async for event in result:
                yield event
            setattr(context, context_attr, None)  # no “value result”

        else:
            # Normal async return
            result = await result

            # Case 2 — value (e.g., modified_input)
            if not isinstance(result, AgentEvent):
                setattr(context, context_attr, result)

                yield AgentEvent(
                    type="execute_callback_result",
                    content=f"Modified user input: {result}",
                    callback_type=callback_type
                )

            # Case 3 — event
            elif isinstance(result, AgentEvent):
                getattr(context, context_attr).append(result)
                yield result

            # Case 4 — list of events
            elif isinstance(result, list):
                for ev in result:
                    if isinstance(ev, AgentEvent):
                        getattr(context, context_attr).append(ev)
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