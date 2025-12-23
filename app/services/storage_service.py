from google.cloud import storage
from google.oauth2 import service_account
import datetime
import asyncio
from typing import Optional
from functools import lru_cache

from app.core.logging import get_logger
from app.core.config import settings
from app.schemas.chat import Citation, Message

logger = get_logger(__name__)


class StorageService:
	def __init__(self, project_id: Optional[str] = None):
		self.project_id = project_id
		self._client = None

	@property
	def client(self) -> storage.Client:
		"""
		Storage client requires servcie account identity, namely private key to sign URLs.
		Regular gcloud auth is not sufficient.
		"""

		if not settings.GCP_CREDENTIALS_JSON:
			raise EnvironmentError(
				"GCP credentials not configured for StorageService."
			)

		if self._client is None:
			credentials = service_account.Credentials.from_service_account_info(
				settings.GCP_CREDENTIALS_JSON
			)
			self._client = storage.Client(
				credentials=credentials, project=self.project_id
			)

		return self._client

	def generate_signed_url(
		self, gcs_path: str, expiration: int = 3600
	) -> Optional[str]:
		"""
		Generates a signed URL for a GCS object.

		Args:
		    gcs_path: Full GCS path (e.g., gs://bucket-name/path/to/object)
		    expiration: Expiration time in seconds (default 1 hour)

		Returns:
		    Signed URL string or None if path is invalid
		"""
		if not gcs_path.startswith("gs://"):
			return None

		path_parts = gcs_path[5:].split("/", 1)
		if len(path_parts) != 2:
			return None

		bucket_name, blob_name = path_parts

		bucket = self.client.bucket(bucket_name)
		blob = bucket.blob(blob_name)

		url = blob.generate_signed_url(
			version="v4",
			expiration=datetime.timedelta(seconds=expiration),
			method="GET",
		)
		return url

	# async def refresh_citations_signed_urls(
	#         self, messages: list[Message], expiration: int = 3600
	#     ) -> list[Message]:
	#     """
	#     Refresh signed URLs for a list of citations in place.

	#     Args:
	#         citations: List of citation objects with gcs_path and url attributes
	#         expiration: Expiration time in seconds for the signed URLs
	#     """
	#     for msg in messages:
	#         logger.info(msg)
	#         for trace in (msg.traces or []):
	#             for c in (trace.citations or []):
	#                 if (not c.url) and c.gcs_path:
	#                     c.url = self.generate_signed_url(c.gcs_path, expiration=expiration)
	#     return messages

	async def refresh_citations_signed_urls(
		self, messages: list[Message], expiration: int = 3600
	) -> list[Message]:
		"""
		Refresh signed URLs for citations concurrently with a semaphore to limit concurrency.
		"""
		sem = asyncio.Semaphore(20)

		async def _sign(gcs_path: str) -> Optional[str]:
			async with sem:
				return await asyncio.to_thread(
					self.generate_signed_url, gcs_path, expiration
				)

		pending: list[asyncio.Task] = []
		refs: list[Citation] = []

		for msg in messages:
			for trace in msg.traces or []:
				for c in trace.citations or []:
					if c.gcs_path:
						refs.append(c)
						pending.append(asyncio.create_task(_sign(c.gcs_path)))

		if pending:
			results = await asyncio.gather(*pending, return_exceptions=True)
			for c, r in zip(refs, results):
				if isinstance(r, Exception):
					logger.exception("Failed generating signed URL", exc_info=r)
					continue
				c.url = r


@lru_cache()
def get_storage_service() -> StorageService:
	return StorageService()
