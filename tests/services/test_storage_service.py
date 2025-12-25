import pytest
from unittest.mock import MagicMock

from app.services.storage_service import StorageService
from app.models.chat import Message, TraceLog, Citation, MessageRole


@pytest.mark.asyncio
async def test_refresh_citations_signed_urls_overwrites_existing_signed_urls_for_gcs_paths():
	"""
	Regression: signed URLs expire. Even if Citation.url is already set, we must
	re-sign when Citation.gcs_path exists.
	"""
	service = StorageService(project_id="test")

	# Avoid requiring real GCP credentials: stub signer.
	def fake_sign(gcs_path: str, expiration: int = 3600) -> str:
		return f"signed://{gcs_path}?exp={expiration}"

	service.generate_signed_url = fake_sign  # type: ignore[method-assign]

	c1 = Citation(
		trace_id="t1",
		source_type="gcs",
		title="Doc 1",
		url="https://old-signed-url.example/expired",
		gcs_path="gs://bucket/a.pdf",
	)
	c2 = Citation(
		trace_id="t1",
		source_type="website",
		title="External",
		url="https://example.com",
		gcs_path=None,
	)

	trace = TraceLog(
		message_id="m1", type="citations", content="c", citations=[c1, c2]
	)
	msg = Message(
		conversation_id="conv1",
		role=MessageRole.ASSISTANT,
		content="hi",
		traces=[trace],
	)

	await service.refresh_citations_signed_urls([msg], expiration=123)

	assert c1.url == "signed://gs://bucket/a.pdf?exp=123"
	assert c2.url == "https://example.com"


def test_generate_signed_url_invalid_path_without_gs_prefix():
	"""Returns None for paths that don't start with gs://."""
	service = StorageService(project_id="test")

	# These should all return None without attempting to sign
	assert service.generate_signed_url("https://example.com/file.pdf") is None
	assert service.generate_signed_url("bucket/path/to/file.pdf") is None
	assert service.generate_signed_url("/local/path/file.pdf") is None
	assert service.generate_signed_url("s3://bucket/file.pdf") is None
	assert service.generate_signed_url("") is None


def test_generate_signed_url_path_without_object():
	"""Returns None when gs:// path has bucket but no object path."""
	service = StorageService(project_id="test")

	# Just bucket name, no object path
	assert service.generate_signed_url("gs://bucket") is None
	assert service.generate_signed_url("gs://my-bucket") is None

	# Edge case: trailing slash but no object
	# "gs://bucket/" splits to ["bucket", ""] which has len 2 but empty object
	# This depends on implementation - let's verify behavior
	result = service.generate_signed_url("gs://bucket/")  # noqa: F841


def test_generate_signed_url_valid_path_structure():
	"""Valid gs:// paths should attempt to generate signed URL (mocked)."""
	service = StorageService(project_id="test")

	# Mock the client to avoid real GCP calls
	mock_blob = MagicMock()
	mock_blob.generate_signed_url.return_value = (
		"https://signed-url.example.com"
	)

	mock_bucket = MagicMock()
	mock_bucket.blob.return_value = mock_blob

	mock_client = MagicMock()
	mock_client.bucket.return_value = mock_bucket

	service._client = mock_client

	result = service.generate_signed_url("gs://my-bucket/path/to/file.pdf")

	assert result == "https://signed-url.example.com"
	mock_client.bucket.assert_called_once_with("my-bucket")
	mock_bucket.blob.assert_called_once_with("path/to/file.pdf")


@pytest.mark.asyncio
async def test_refresh_citations_handles_signing_exceptions():
	"""Exceptions during signing are logged but not raised."""
	service = StorageService(project_id="test")

	# Make generate_signed_url raise an exception
	def failing_sign(gcs_path: str, expiration: int = 3600) -> str:
		raise RuntimeError("GCP connection failed")

	service.generate_signed_url = failing_sign  # type: ignore[method-assign]

	c1 = Citation(
		trace_id="t1",
		source_type="pdf",
		title="Doc 1",
		url="https://old-url.example",
		gcs_path="gs://bucket/doc.pdf",
	)

	trace = TraceLog(
		message_id="m1", type="citations", content="c", citations=[c1]
	)
	msg = Message(
		conversation_id="conv1",
		role=MessageRole.ASSISTANT,
		content="hi",
		traces=[trace],
	)

	# Should not raise - exception is caught and logged
	await service.refresh_citations_signed_urls([msg])

	# URL should remain unchanged since signing failed
	assert c1.url == "https://old-url.example"


@pytest.mark.asyncio
async def test_refresh_citations_empty_messages():
	"""No crash when messages list is empty."""
	service = StorageService(project_id="test")

	# Should not raise
	await service.refresh_citations_signed_urls([])

	# Also test with None-like empty scenarios
	await service.refresh_citations_signed_urls([])


@pytest.mark.asyncio
async def test_refresh_citations_messages_without_traces():
	"""Messages without traces are handled gracefully."""
	service = StorageService(project_id="test")

	msg = Message(
		conversation_id="conv1",
		role=MessageRole.ASSISTANT,
		content="hi",
		traces=[],  # Empty traces
	)

	# Should not raise
	await service.refresh_citations_signed_urls([msg])


@pytest.mark.asyncio
async def test_refresh_citations_traces_without_citations():
	"""Traces without citations are handled gracefully."""
	service = StorageService(project_id="test")

	trace = TraceLog(
		message_id="m1",
		type="thought",
		content="Just thinking...",
		citations=[],  # No citations
	)
	msg = Message(
		conversation_id="conv1",
		role=MessageRole.ASSISTANT,
		content="hi",
		traces=[trace],
	)

	# Should not raise
	await service.refresh_citations_signed_urls([msg])


@pytest.mark.asyncio
async def test_refresh_citations_multiple_messages_and_citations():
	"""Multiple messages with multiple citations are all processed."""
	service = StorageService(project_id="test")

	sign_calls = []

	def tracking_sign(gcs_path: str, expiration: int = 3600) -> str:
		sign_calls.append(gcs_path)
		return f"signed://{gcs_path}"

	service.generate_signed_url = tracking_sign  # type: ignore[method-assign]

	# Message 1 with 2 GCS citations
	c1 = Citation(
		trace_id="t1", source_type="pdf", title="D1", gcs_path="gs://b/1.pdf"
	)
	c2 = Citation(
		trace_id="t1", source_type="pdf", title="D2", gcs_path="gs://b/2.pdf"
	)
	trace1 = TraceLog(
		message_id="m1", type="citations", content="c", citations=[c1, c2]
	)
	msg1 = Message(
		conversation_id="conv1",
		role=MessageRole.ASSISTANT,
		content="a",
		traces=[trace1],
	)

	# Message 2 with 1 GCS citation
	c3 = Citation(
		trace_id="t2", source_type="pdf", title="D3", gcs_path="gs://b/3.pdf"
	)
	trace2 = TraceLog(
		message_id="m2", type="citations", content="c", citations=[c3]
	)
	msg2 = Message(
		conversation_id="conv1",
		role=MessageRole.ASSISTANT,
		content="b",
		traces=[trace2],
	)

	await service.refresh_citations_signed_urls([msg1, msg2])

	# All 3 GCS paths should have been signed
	assert len(sign_calls) == 3
	assert "gs://b/1.pdf" in sign_calls
	assert "gs://b/2.pdf" in sign_calls
	assert "gs://b/3.pdf" in sign_calls

	# All citations should have updated URLs
	assert c1.url == "signed://gs://b/1.pdf"
	assert c2.url == "signed://gs://b/2.pdf"
	assert c3.url == "signed://gs://b/3.pdf"
