"""HTML processing and text extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class HTMLProcessingResult:
    """Result of HTML processing."""

    original_path: Path
    markdown_path: Optional[Path] = None
    text_content: str = ""
    title: Optional[str] = None
    word_count: int = 0


class HTMLProcessor:
    """Process HTML documents to clean markdown.

    Uses trafilatura for article extraction when available,
    falls back to BeautifulSoup for general HTML.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize HTML processor.

        Args:
            output_dir: Directory for output files.
        """
        self.output_dir = output_dir or Path("data/processed/markdown")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process(
        self,
        html_path: Path | str,
        encoding: str = "utf-8",
    ) -> HTMLProcessingResult:
        """Process an HTML file to markdown.

        Args:
            html_path: Path to HTML file.
            encoding: File encoding.

        Returns:
            HTMLProcessingResult with extracted content.
        """
        html_path = Path(html_path)

        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        result = HTMLProcessingResult(original_path=html_path)

        # Read HTML content
        html_content = html_path.read_text(encoding=encoding, errors="replace")

        # Try trafilatura first (best for articles)
        markdown_content = self._extract_with_trafilatura(html_content)

        if not markdown_content:
            # Fall back to BeautifulSoup
            markdown_content, title = self._extract_with_beautifulsoup(html_content)
            result.title = title
        else:
            result.title = self._extract_title(html_content)

        result.text_content = markdown_content
        result.word_count = len(markdown_content.split())

        # Save markdown file
        if markdown_content:
            md_path = self.output_dir / f"{html_path.stem}.md"
            md_path.write_text(markdown_content, encoding="utf-8")
            result.markdown_path = md_path

        return result

    def _extract_with_trafilatura(self, html_content: str) -> str:
        """Extract content using trafilatura."""
        try:
            import trafilatura

            result = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                output_format="markdown",
            )
            return result or ""

        except ImportError:
            return ""
        except Exception:
            return ""

    def _extract_with_beautifulsoup(self, html_content: str) -> tuple[str, Optional[str]]:
        """Extract content using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Get title
            title = None
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()

            # Remove scripts, styles, nav, footer, etc.
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                element.decompose()

            # Try to find main content
            main_content = soup.find("main") or soup.find("article") or soup.find("body")

            if main_content:
                # Convert to text with basic markdown
                text = self._html_to_markdown(main_content)
            else:
                text = soup.get_text(separator="\n")

            # Clean up whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = text.strip()

            return text, title

        except ImportError:
            return "", None
        except Exception:
            return "", None

    def _extract_title(self, html_content: str) -> Optional[str]:
        """Extract title from HTML."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")
            title_tag = soup.find("title")
            return title_tag.get_text().strip() if title_tag else None

        except Exception:
            return None

    def _html_to_markdown(self, element) -> str:
        """Convert HTML element to basic markdown."""
        lines = []

        for child in element.children:
            if hasattr(child, "name"):
                tag = child.name

                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    level = int(tag[1])
                    text = child.get_text().strip()
                    if text:
                        lines.append(f"{'#' * level} {text}\n")

                elif tag == "p":
                    text = child.get_text().strip()
                    if text:
                        lines.append(f"{text}\n")

                elif tag in ("ul", "ol"):
                    for li in child.find_all("li", recursive=False):
                        text = li.get_text().strip()
                        if text:
                            prefix = "-" if tag == "ul" else "1."
                            lines.append(f"{prefix} {text}")
                    lines.append("")

                elif tag == "blockquote":
                    text = child.get_text().strip()
                    if text:
                        lines.append(f"> {text}\n")

                elif tag == "pre":
                    text = child.get_text()
                    lines.append(f"```\n{text}\n```\n")

                elif tag in ("div", "section", "article"):
                    # Recurse into container elements
                    lines.append(self._html_to_markdown(child))

            elif hasattr(child, "strip"):
                # Text node
                text = child.strip()
                if text:
                    lines.append(text)

        return "\n".join(lines)

    def process_url(self, url: str) -> HTMLProcessingResult:
        """Fetch and process HTML from a URL.

        Args:
            url: URL to fetch.

        Returns:
            HTMLProcessingResult with extracted content.
        """
        try:
            import trafilatura

            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    output_format="markdown",
                )

                result = HTMLProcessingResult(
                    original_path=Path(url),
                    text_content=content or "",
                    word_count=len((content or "").split()),
                )

                return result

        except ImportError:
            pass
        except Exception:
            pass

        return HTMLProcessingResult(original_path=Path(url))
