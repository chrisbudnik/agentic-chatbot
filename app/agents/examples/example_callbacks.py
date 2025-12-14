from typing import AsyncIterator, List

from app.agents.models import CallbackContext, AgentEvent


async def example_before_agent_callback(
	user_input: str, history: List[dict], context: CallbackContext
) -> str:
	"""
	Before agent callbacks operate on user_input and history before it is processed by the agent.

	In this example, callback will convert user prompt to uppercase.
	Implementation: async function that returns string.

	Valid use cases include:
	    - automatic context injection (user context, preferences, RAG snippets)
	    - user prompt enhancement - e.g., adding instructions
	    - Decision if to proceed with the agent or return a canned response
	    - Logging / analytics
	    - Custom history manipulation - e.g., summarization, filtering, formatting, trimming

	IMPORTANT: if saving to context, set context.modified_input to the modified value.

	Callbacks can be impelemented in several ways:
	    - async generators (recommended) - yield AgentEvents with process updates, save return value in context
	    - async function - return list of events (to be emitted at onece when callback completes), save return in context
	    - async function - return modified user_input directly (str)

	Args:
	    user_input: The original user input.
	    history: The conversation history.
	    context: The callback context.
	"""

	return user_input.upper()


async def example_after_agent_callback(
	final_answer: AgentEvent, context: CallbackContext
) -> List[AgentEvent]:
	"""
	After agent callbacks operate on the final answer produced by the agent.

	In this example, callback will add an extra thought before the final answer.
	Implementation: async function that returns list of AgentEvents.

	Valid use cases include:
	    - adding citations / sources (via callback context or emitting events)
	    - change / check language
	    - adding extra thoughts / explanations
	    - logging / analytics
	    - modifying final answer formatting
	    - adding assets (images etc.)

	IMPORTANT: if saving to context, set context.after_events to the modified value.

	Args:
	    final_answer: The final answer produced by the agent.
	    context: The callback context.
	"""

	extra_event = AgentEvent(
		type="thought",
		content="This thought was added by the after_agent_callback.",
	)
	return [extra_event, final_answer]


async def example_before_tool_callback(
	tool_args: dict, context: CallbackContext
) -> AsyncIterator[AgentEvent]:
	"""
	Before tool callbacks operate on tool arguments before the tool is executed.

	In this example, callback will append a string to the 'query' argument and convert to lowercase.
	Implementation: async generator, return value via context.

	Valid use cases include:
	    - modifying tool arguments based on context
	    - logging / analytics
	    - adding authentication / api keys
	    - input validation / correction

	IMPORTANT: if saving to context, set context.tool_input to the modified value.
	"""
	modified_args = tool_args.copy()
	if "query" in modified_args:
		modified_args["query"] = modified_args["query"].lower()

	yield AgentEvent(
		type="thought",
		content=f"Modified tool arguments in before_tool_callback: {modified_args}",
	)

	context.tool_input = modified_args


async def example_after_tool_callback(
	tool_result: str, context: CallbackContext
) -> None:
	"""
	After tool callbacks operate on the tool result after the tool has been executed.

	In this example, callback will append a string to the tool result.
	Implementation: async function that returns modified tool result.

	Valid use cases include:
	    - modifying tool results based on context
	    - logging / analytics
	    - result validation / correction

	IMPORTANT: if saving to context, set context.tool_result to the modified value.

	Args:
	    tool_result: The result produced by the tool.
	    context: The callback context.
	"""
	modified_result = tool_result + " (sources are not verified)"
	context.tool_result = modified_result
