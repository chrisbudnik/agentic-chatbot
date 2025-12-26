import pytest
from app.agents.utils import require_context, MissingContextAttributeError
from app.agents.models import CallbackContext


# ============================================================
# SYNC FUNCTION TESTS
# ============================================================


def test_require_context_sync_valid():
	"""Sync callback passes when required context attributes are set."""

	@require_context(["modified_input"])
	def my_callback(context: CallbackContext):
		return f"Got: {context.modified_input}"

	ctx = CallbackContext()
	ctx.modified_input = "test_value"

	result = my_callback(context=ctx)
	assert result == "Got: test_value"


def test_require_context_sync_missing_raises():
	"""Sync callback raises when required attribute is None."""

	@require_context(["tool_result"])
	def my_callback(context: CallbackContext):
		return context.tool_result

	ctx = CallbackContext()
	# tool_result is None by default

	with pytest.raises(MissingContextAttributeError) as exc_info:
		my_callback(context=ctx)

	assert "tool_result" in exc_info.value.missing_attrs
	assert exc_info.value.callback_name == "my_callback"


# ============================================================
# ASYNC FUNCTION TESTS
# ============================================================


@pytest.mark.asyncio
async def test_require_context_async_valid():
	"""Async callback passes when required context attributes are set."""

	@require_context(["llm_result"])
	async def my_async_callback(context: CallbackContext):
		return f"LLM: {context.llm_result}"

	ctx = CallbackContext()
	ctx.llm_result = "model_response"

	result = await my_async_callback(context=ctx)
	assert result == "LLM: model_response"


@pytest.mark.asyncio
async def test_require_context_async_missing_raises():
	"""Async callback raises when required attribute is None."""

	@require_context(["final_answer"])
	async def my_async_callback(context: CallbackContext):
		return context.final_answer

	ctx = CallbackContext()

	with pytest.raises(MissingContextAttributeError) as exc_info:
		await my_async_callback(context=ctx)

	assert "final_answer" in exc_info.value.missing_attrs


# ============================================================
# ASYNC GENERATOR TESTS
# ============================================================


@pytest.mark.asyncio
async def test_require_context_asyncgen_valid():
	"""Async generator passes when required context attributes are set."""

	@require_context(["tool_input"])
	async def my_gen_callback(context: CallbackContext):
		yield f"Processing: {context.tool_input}"
		yield "Done"

	ctx = CallbackContext()
	ctx.tool_input = {"query": "test"}

	results = []
	async for item in my_gen_callback(context=ctx):
		results.append(item)

	assert results == ["Processing: {'query': 'test'}", "Done"]


@pytest.mark.asyncio
async def test_require_context_asyncgen_missing_raises():
	"""Async generator raises when required attribute is None."""

	@require_context(["llm_params"])
	async def my_gen_callback(context: CallbackContext):
		yield context.llm_params

	ctx = CallbackContext()

	with pytest.raises(MissingContextAttributeError):
		async for _ in my_gen_callback(context=ctx):
			pass


# ============================================================
# MULTIPLE ATTRIBUTES TESTS
# ============================================================


def test_require_context_multiple_attrs_all_valid():
	"""Passes when all multiple required attributes are set."""

	@require_context(["modified_input", "tool_result", "llm_result"])
	def my_callback(context: CallbackContext):
		return "all_good"

	ctx = CallbackContext()
	ctx.modified_input = "input"
	ctx.tool_result = "tool"
	ctx.llm_result = "llm"

	result = my_callback(context=ctx)
	assert result == "all_good"


def test_require_context_multiple_attrs_partial_missing():
	"""Raises when some of multiple required attributes are missing."""

	@require_context(["modified_input", "tool_result", "llm_result"])
	def my_callback(context: CallbackContext):
		return "won't reach"

	ctx = CallbackContext()
	ctx.modified_input = "input"
	# tool_result and llm_result are None

	with pytest.raises(MissingContextAttributeError) as exc_info:
		my_callback(context=ctx)

	assert "tool_result" in exc_info.value.missing_attrs
	assert "llm_result" in exc_info.value.missing_attrs
	assert "modified_input" not in exc_info.value.missing_attrs


# ============================================================
# CONTEXT EXTRACTION TESTS
# ============================================================


def test_require_context_positional_arg():
	"""Context can be passed as positional argument."""

	@require_context(["modified_input"])
	def my_callback(data: str, context: CallbackContext):
		return f"{data}: {context.modified_input}"

	ctx = CallbackContext()
	ctx.modified_input = "value"

	result = my_callback("prefix", ctx)
	assert result == "prefix: value"


def test_require_context_no_context_raises():
	"""Raises ValueError when context is not in arguments."""

	@require_context(["modified_input"])
	def my_callback(data: str):
		return data

	with pytest.raises(ValueError) as exc_info:
		my_callback("test")

	assert "CallbackContext not found" in str(exc_info.value)


# ============================================================
# EDGE CASES
# ============================================================


def test_require_context_empty_list():
	"""Empty required_attrs list always passes."""

	@require_context([])
	def my_callback(context: CallbackContext):
		return "no requirements"

	ctx = CallbackContext()
	result = my_callback(context=ctx)
	assert result == "no requirements"


def test_require_context_nonexistent_attr():
	"""Reports when attribute doesn't exist on context."""

	@require_context(["nonexistent_field"])
	def my_callback(context: CallbackContext):
		return "won't reach"

	ctx = CallbackContext()

	with pytest.raises(MissingContextAttributeError) as exc_info:
		my_callback(context=ctx)

	# Should indicate the attribute doesn't exist
	assert any(
		"does not exist" in attr for attr in exc_info.value.missing_attrs
	)
