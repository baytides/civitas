"""Azure Blob Storage client for storing scraped legal data.

Storage structure:
    civitas-data/
    ├── opinions/
    │   ├── scotus/2024/case_id.pdf
    │   ├── courtlistener/2024/case_id.json
    │   └── ...
    ├── legislation/
    │   ├── federal/118/bill_id.json
    │   ├── california/2024/bill_id.json
    │   └── ...
    ├── reference/
    │   └── project2025/mandate_for_leadership.pdf
    ├── backups/
    │   └── database/civitas_20240115_120000.db
    └── ...

Configuration:
    Set AZURE_STORAGE_CONNECTION_STRING environment variable, or pass
    connection_string to AzureStorageClient.

    Storage account: baytidesstorage (westus2)
    Container: civitas-data
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import BinaryIO


class AzureStorageClient:
    """Client for Azure Blob Storage.

    Stores:
    - Raw scraped documents (PDFs, HTML)
    - Parsed JSON data
    - Database backups
    - Reference documents (Project 2025, etc.)
    """

    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str = "civitas-data",
    ):
        """Initialize Azure Storage client.

        Args:
            connection_string: Azure Storage connection string.
                              Falls back to AZURE_STORAGE_CONNECTION_STRING env var.
            container_name: Container name (default: civitas-data)
        """
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = container_name
        self._client = None
        self._container_client = None

    def _get_client(self):
        """Lazy load the Azure client."""
        if self._client is None:
            try:
                from azure.storage.blob import BlobServiceClient
            except ImportError:
                raise ImportError(
                    "Azure Storage SDK not installed. Install with: pip install azure-storage-blob"
                )

            if not self.connection_string:
                raise ValueError(
                    "AZURE_STORAGE_CONNECTION_STRING not set. "
                    "Set environment variable or pass connection_string to constructor."
                )

            self._client = BlobServiceClient.from_connection_string(self.connection_string)

            # Create container if it doesn't exist
            try:
                self._client.create_container(self.container_name)
            except Exception:
                pass  # Container already exists

        return self._client

    def _get_container(self):
        """Get container client."""
        if self._container_client is None:
            self._container_client = self._get_client().get_container_client(self.container_name)
        return self._container_client

    def upload_document(
        self,
        data: bytes | BinaryIO,
        document_type: str,
        source: str,
        document_id: str,
        file_extension: str = "pdf",
        year: int | None = None,
    ) -> str:
        """Upload a document to Azure Blob Storage.

        Args:
            data: File content (bytes or file-like object)
            document_type: Type of document (opinion, legislation, reference)
            source: Source identifier (scotus, courtlistener, california, federal)
            document_id: Unique document identifier
            file_extension: File extension (pdf, json, html)
            year: Optional year for organization (defaults to current year)

        Returns:
            The blob URL

        Example:
            >>> client.upload_document(
            ...     pdf_bytes, "opinion", "scotus", "22-1234", "pdf"
            ... )
            'https://baytidesstorage.blob.core.windows.net/civitas-data/opinion/scotus/2024/22-1234.pdf'
        """
        container = self._get_container()

        # Organize by type/source/year/id
        year = year or datetime.now().year
        blob_name = f"{document_type}/{source}/{year}/{document_id}.{file_extension}"

        blob_client = container.get_blob_client(blob_name)

        if isinstance(data, bytes):
            blob_client.upload_blob(data, overwrite=True)
        else:
            blob_client.upload_blob(data.read(), overwrite=True)

        return blob_client.url

    def upload_json(
        self,
        data: dict,
        document_type: str,
        source: str,
        document_id: str,
        year: int | None = None,
    ) -> str:
        """Upload JSON data to Azure.

        Args:
            data: Dictionary to serialize as JSON
            document_type: Type of document
            source: Source identifier
            document_id: Unique document identifier
            year: Optional year for organization

        Returns:
            The blob URL
        """
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")
        return self.upload_document(json_bytes, document_type, source, document_id, "json", year)

    def upload_reference(
        self,
        data: bytes | BinaryIO,
        name: str,
        file_extension: str = "pdf",
    ) -> str:
        """Upload a reference document (e.g., Project 2025).

        Args:
            data: File content
            name: Document name (e.g., "project2025/mandate_for_leadership")
            file_extension: File extension

        Returns:
            The blob URL
        """
        container = self._get_container()
        blob_name = f"reference/{name}.{file_extension}"
        blob_client = container.get_blob_client(blob_name)

        if isinstance(data, bytes):
            blob_client.upload_blob(data, overwrite=True)
        else:
            blob_client.upload_blob(data.read(), overwrite=True)

        return blob_client.url

    def download_document(self, blob_name: str) -> bytes:
        """Download a document from Azure.

        Args:
            blob_name: Full blob path (e.g., "opinion/scotus/2024/22-1234.pdf")

        Returns:
            Document content as bytes
        """
        container = self._get_container()
        blob_client = container.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def download_json(self, blob_name: str) -> dict:
        """Download and parse a JSON document.

        Args:
            blob_name: Full blob path

        Returns:
            Parsed JSON as dictionary
        """
        data = self.download_document(blob_name)
        return json.loads(data.decode("utf-8"))

    def list_documents(
        self,
        document_type: str | None = None,
        source: str | None = None,
        year: int | None = None,
    ) -> list[str]:
        """List documents in storage.

        Args:
            document_type: Filter by document type
            source: Filter by source
            year: Filter by year

        Returns:
            List of blob names matching filters
        """
        container = self._get_container()

        prefix = ""
        if document_type:
            prefix = f"{document_type}/"
            if source:
                prefix = f"{document_type}/{source}/"
                if year:
                    prefix = f"{document_type}/{source}/{year}/"

        return [blob.name for blob in container.list_blobs(name_starts_with=prefix)]

    def document_exists(self, blob_name: str) -> bool:
        """Check if a document exists.

        Args:
            blob_name: Full blob path

        Returns:
            True if document exists
        """
        container = self._get_container()
        blob_client = container.get_blob_client(blob_name)
        return blob_client.exists()

    def get_document_url(self, blob_name: str) -> str:
        """Get the URL for a document.

        Args:
            blob_name: Full blob path

        Returns:
            Full URL to the blob
        """
        container = self._get_container()
        blob_client = container.get_blob_client(blob_name)
        return blob_client.url

    def backup_database(self, db_path: str = "civitas.db") -> str:
        """Backup the SQLite database to Azure.

        Args:
            db_path: Path to the SQLite database file

        Returns:
            The blob URL of the backup
        """
        with open(db_path, "rb") as f:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"backups/database/civitas_{timestamp}.db"

            container = self._get_container()
            blob_client = container.get_blob_client(blob_name)
            blob_client.upload_blob(f.read(), overwrite=True)

            return blob_client.url

    def list_backups(self) -> list[dict]:
        """List available database backups.

        Returns:
            List of backup info dictionaries with name, size, created_at
        """
        container = self._get_container()
        backups = []

        for blob in container.list_blobs(name_starts_with="backups/database/"):
            backups.append(
                {
                    "name": blob.name,
                    "size": blob.size,
                    "created_at": blob.creation_time,
                }
            )

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def restore_database(self, blob_name: str, db_path: str = "civitas.db") -> None:
        """Restore a database from Azure backup.

        Args:
            blob_name: Backup blob name
            db_path: Local path to restore to
        """
        data = self.download_document(blob_name)
        with open(db_path, "wb") as f:
            f.write(data)

    def delete_document(self, blob_name: str) -> None:
        """Delete a document from storage.

        Args:
            blob_name: Full blob path
        """
        container = self._get_container()
        blob_client = container.get_blob_client(blob_name)
        blob_client.delete_blob()

    def get_storage_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with counts and sizes by document type
        """
        container = self._get_container()
        stats = {
            "total_blobs": 0,
            "total_size_bytes": 0,
            "by_type": {},
        }

        for blob in container.list_blobs():
            stats["total_blobs"] += 1
            stats["total_size_bytes"] += blob.size or 0

            # Extract document type from path
            parts = blob.name.split("/")
            if parts:
                doc_type = parts[0]
                if doc_type not in stats["by_type"]:
                    stats["by_type"][doc_type] = {"count": 0, "size_bytes": 0}
                stats["by_type"][doc_type]["count"] += 1
                stats["by_type"][doc_type]["size_bytes"] += blob.size or 0

        return stats


class LocalStorageClient:
    """Local file storage client for development/testing.

    Mirrors the AzureStorageClient interface but uses local filesystem.
    """

    def __init__(self, base_dir: str = "data"):
        """Initialize local storage client.

        Args:
            base_dir: Base directory for storage (default: data/)
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload_document(
        self,
        data: bytes | BinaryIO,
        document_type: str,
        source: str,
        document_id: str,
        file_extension: str = "pdf",
        year: int | None = None,
    ) -> str:
        """Upload a document to local storage."""
        year = year or datetime.now().year
        path = self.base_dir / document_type / source / str(year)
        path.mkdir(parents=True, exist_ok=True)

        filepath = path / f"{document_id}.{file_extension}"

        if isinstance(data, bytes):
            filepath.write_bytes(data)
        else:
            filepath.write_bytes(data.read())

        return str(filepath)

    def upload_json(
        self,
        data: dict,
        document_type: str,
        source: str,
        document_id: str,
        year: int | None = None,
    ) -> str:
        """Upload JSON data to local storage."""
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")
        return self.upload_document(json_bytes, document_type, source, document_id, "json", year)

    def upload_reference(
        self,
        data: bytes | BinaryIO,
        name: str,
        file_extension: str = "pdf",
    ) -> str:
        """Upload a reference document."""
        path = self.base_dir / "reference"
        path.mkdir(parents=True, exist_ok=True)

        # Handle nested names like "project2025/mandate"
        filepath = path / f"{name}.{file_extension}"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            filepath.write_bytes(data)
        else:
            filepath.write_bytes(data.read())

        return str(filepath)

    def download_document(self, path: str) -> bytes:
        """Download a document from local storage."""
        return Path(path).read_bytes()

    def download_json(self, path: str) -> dict:
        """Download and parse a JSON document."""
        data = self.download_document(path)
        return json.loads(data.decode("utf-8"))

    def list_documents(
        self,
        document_type: str | None = None,
        source: str | None = None,
        year: int | None = None,
    ) -> list[str]:
        """List documents in storage."""
        search_path = self.base_dir
        if document_type:
            search_path = search_path / document_type
            if source:
                search_path = search_path / source
                if year:
                    search_path = search_path / str(year)

        if not search_path.exists():
            return []

        return [str(p) for p in search_path.rglob("*") if p.is_file()]

    def document_exists(self, path: str) -> bool:
        """Check if a document exists."""
        return Path(path).exists()

    def backup_database(self, db_path: str = "civitas.db") -> str:
        """Backup the database to local storage."""
        backup_dir = self.base_dir / "backups" / "database"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"civitas_{timestamp}.db"

        import shutil

        shutil.copy2(db_path, backup_path)

        return str(backup_path)
