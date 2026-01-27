"""Storage backends for Civitas.

Supports:
- Azure Blob Storage (production)
- Local file storage (development)
"""

from .azure_blob import AzureStorageClient

__all__ = ["AzureStorageClient"]
