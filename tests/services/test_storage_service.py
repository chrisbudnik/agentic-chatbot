import pytest

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
