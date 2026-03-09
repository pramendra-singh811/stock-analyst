"""Manage documents for each stock project."""

import base64
import mimetypes
import shutil
from pathlib import Path

from ..utils.config import get_project_dir


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv", ".json", ".md", ".docx", ".xlsx"}


class DocumentManager:
    """Handles document storage and retrieval for a stock project."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.project_dir = get_project_dir(self.ticker)
        self.docs_dir = self.project_dir / "documents"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def add_document(self, file_path: str | Path, category: str = "general") -> Path:
        """Copy a document into the project's document store.

        Args:
            file_path: Path to the source file.
            category: Subfolder category (e.g. 'annual_reports', 'quarterly',
                      'transcripts', 'industry').

        Returns:
            Path to the stored copy.
        """
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"File not found: {src}")
        if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {src.suffix}. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            )

        category_dir = self.docs_dir / category
        category_dir.mkdir(exist_ok=True)
        dest = category_dir / src.name
        shutil.copy2(src, dest)
        return dest

    def list_documents(self, category: str | None = None) -> list[dict]:
        """List all documents, optionally filtered by category."""
        results = []
        search_dir = self.docs_dir / category if category else self.docs_dir
        if not search_dir.exists():
            return results
        for path in sorted(search_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                results.append(
                    {
                        "name": path.name,
                        "category": path.parent.name
                        if path.parent != self.docs_dir
                        else "general",
                        "path": str(path),
                        "size_kb": round(path.stat().st_size / 1024, 1),
                    }
                )
        return results

    def remove_document(self, filename: str, category: str = "general") -> bool:
        """Remove a document from the store."""
        target = self.docs_dir / category / filename
        if target.exists():
            target.unlink()
            return True
        # Try searching all categories
        for path in self.docs_dir.rglob(filename):
            if path.is_file():
                path.unlink()
                return True
        return False

    def prepare_for_api(self) -> list[dict]:
        """Prepare all documents as content blocks for the Claude API.

        Returns a list of content blocks suitable for the messages API.
        PDFs are sent as base64-encoded document blocks.
        Text files are sent as text content.
        """
        content_blocks = []
        for doc in self.list_documents():
            path = Path(doc["path"])
            if path.suffix.lower() == ".pdf":
                with open(path, "rb") as f:
                    data = base64.standard_b64encode(f.read()).decode("utf-8")
                content_blocks.append(
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": data,
                        },
                        "title": doc["name"],
                    }
                )
            elif path.suffix.lower() in {".txt", ".csv", ".md", ".json"}:
                text = path.read_text(errors="replace")
                content_blocks.append(
                    {
                        "type": "text",
                        "text": f"--- Document: {doc['name']} ---\n\n{text}",
                    }
                )
            # .docx / .xlsx are uploaded as base64 with appropriate media type
            elif path.suffix.lower() == ".docx":
                mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                with open(path, "rb") as f:
                    data = base64.standard_b64encode(f.read()).decode("utf-8")
                content_blocks.append(
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": mime, "data": data},
                        "title": doc["name"],
                    }
                )
            elif path.suffix.lower() == ".xlsx":
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                with open(path, "rb") as f:
                    data = base64.standard_b64encode(f.read()).decode("utf-8")
                content_blocks.append(
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": mime, "data": data},
                        "title": doc["name"],
                    }
                )
        return content_blocks

    def get_document_summary(self) -> str:
        """Return a human-readable summary of stored documents."""
        docs = self.list_documents()
        if not docs:
            return "No documents uploaded yet."
        lines = [f"Documents for {self.ticker} ({len(docs)} files):"]
        by_cat: dict[str, list] = {}
        for d in docs:
            by_cat.setdefault(d["category"], []).append(d)
        for cat, items in sorted(by_cat.items()):
            lines.append(f"\n  [{cat}]")
            for item in items:
                lines.append(f"    - {item['name']} ({item['size_kb']} KB)")
        return "\n".join(lines)
