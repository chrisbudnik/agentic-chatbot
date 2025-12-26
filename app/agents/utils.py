from functools import wraps
from typing import Callable, List
from app.agents.models import CallbackContext


# ------------------------------------------------------------
# CONTEXT VALIDATION DECORATOR
# ------------------------------------------------------------


class MissingContextAttributeError(Exception):
	"""Raised when a required context attribute is missing or None."""

	def __init__(self, callback_name: str, missing_attrs: List[str]):
		self.callback_name = callback_name
		self.missing_attrs = missing_attrs
		super().__init__(
			f"Callback '{callback_name}' requires context attributes "
			f"{missing_attrs} to be set (not None)"
		)


def require_context(required_attrs: List[str]) -> Callable:
	"""
	    Decorator that validates required attributes on
	CallbackContext before execution of callback function.
	    Use this to ensure upstream callbacks have set the
	    required context fields.

	    Args:
	 required_attrs: List of context attribute
	    names that must be set (not None).

	    Raises:
	 MissingContextAttributeError: If any required
	    attribute is missing or None.

	    Example:
	 @require_context(["tool_result", "llm_result"])
	 async def my_after_tool_callback(tool_result: str, context: CallbackContext):
	     # At this point, context.tool_result and context.llm_result are guaranteed
	     ...
	"""

	def decorator(fn: Callable) -> Callable:
		@wraps(fn)
		def wrapper(*args, **kwargs):
			context = _extract_context(args, kwargs)
			_validate_context(fn.__name__, context, required_attrs)
			return fn(*args, **kwargs)

		return wrapper

	return decorator


def _extract_context(args: tuple, kwargs: dict) -> CallbackContext:
	"""Extract CallbackContext from function arguments."""
	if "context" in kwargs:
		return kwargs["context"]

	for arg in args:
		if isinstance(arg, CallbackContext):
			return arg

	raise ValueError(
		"CallbackContext not found in function arguments. "
		"Ensure 'context' is passed as a keyword argument or positional argument."
	)


def _validate_context(
	callback_name: str, context: CallbackContext, required_attrs: List[str]
) -> None:
	"""Validate that all required attributes are set on the context."""
	missing = []
	for attr in required_attrs:
		if not hasattr(context, attr):
			missing.append(f"{attr} (attribute does not exist)")
		elif getattr(context, attr) is None:
			missing.append(attr)

	if missing:
		raise MissingContextAttributeError(callback_name, missing)
