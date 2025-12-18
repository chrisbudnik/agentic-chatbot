from typing import AsyncIterator, List, Callable, Any
import inspect
from app.agents.models import AgentEvent, CallbackContext


type CallbackFunctionOutput = (
	AsyncIterator[AgentEvent]
	| List[AgentEvent]
	| AgentEvent
	| str
	| dict[str, Any]
	| None
)

type BeforeAgentCallback = Callable[
	[str, List[dict], CallbackContext], CallbackFunctionOutput
]  # user_input: str, history: List[dict]

type AfterAgentCallback = Callable[
	[AgentEvent, CallbackContext], CallbackFunctionOutput
]  # final_answer: AgentEvent

type BeforeToolCallback = Callable[
	[dict[str, Any], CallbackContext], CallbackFunctionOutput
]  # tool_args: dict

type AfterToolCallback = Callable[
	[str, CallbackContext], CallbackFunctionOutput
]  # tool_result: str


async def run_callback_with_events(
	callback_fn: Callable[..., CallbackFunctionOutput],
	callback_input: dict[str, Any],
	context: CallbackContext,
	context_attr: str,
	callback_type: str,
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
		callback_type=callback_type,
	)

	try:
		result = callback_fn(**callback_input, context=context)

		# Case 1 — streaming callback (async gen)
		if inspect.isasyncgen(result):
			async for event in result:
				yield event
			# For streaming callbacks, we rely on the callback to write any
			# "return value" into `context.<context_attr>` (if desired).

		else:
			# Callback may be:
			# - async function (returns awaitable)
			# - sync function (returns a value immediately)
			if inspect.isawaitable(result):
				result = await result

			# Case 2 — single event
			if isinstance(result, AgentEvent):
				yield result

			# Case 3 — list/tuple of events
			elif isinstance(result, (list, tuple)):
				for ev in result:
					if isinstance(ev, AgentEvent):
						yield ev

			# Case 4 — "value" return (string / dict / other)
			elif result is not None:
				setattr(context, context_attr, result)

	except Exception as e:
		yield AgentEvent(
			type="error",
			content=f"{type(e).__name__}: {e}",
			callback_type=callback_type,
		)

	yield AgentEvent(
		type="execute_callback_result",
		content=f"Completed {callback_type} with value: {getattr(context, context_attr)!r}",
		callback_type=callback_type,
	)
