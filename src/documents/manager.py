"""Manage documents for each stock project."""

import shutil
from pathlib import Path

from google.genai import types

from ..utils.config import get_project_dir


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv", ".json", ".md", ".docx", ".xlsx"}

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


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

    def prepare_for_api(self) -> list[types.Part]:
        """Prepare all documents as Gemini API Part objects.

        PDFs and binary files are sent as inline bytes.
        Text files are sent as text parts.

        Returns a list of google.genai.types.Part objects.
        """
        parts = []
        for doc in self.list_documents():
            path = Path(doc["path"])
            ext = path.suffix.lower()
            mime = MIME_TYPES.get(ext, "application/octet-stream")

            if ext in {".txt", ".csv", ".md", ".json"}:
                # Send text files as text content
                text = path.read_text(errors="replace")
                parts.append(
                    types.Part.from_text(
                        text=f"--- Document: {doc['name']} ---\n\n{text}"
                    )
                )
            else:
                # Send binary files (PDF, DOCX, XLSX) as inline bytes
                data = path.read_bytes()
                parts.append(
                    types.Part.from_bytes(data=data, mime_type=mime)
                )
        return parts

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
