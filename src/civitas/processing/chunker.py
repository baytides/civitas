"""Document chunking for AI processing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DocumentChunk:
    """A chunk of a document for AI processing."""

    content: str
    index: int
    token_count: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_title: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class DocumentChunker:
    """Split documents into AI-friendly chunks.

    Chunks are approximately 4000 tokens (suitable for most LLMs),
    with overlap to maintain context across chunks.
    """

    # Approximate chars per token (conservative estimate)
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        max_tokens: int = 4000,
        overlap_tokens: int = 200,
        preserve_sections: bool = True,
    ):
        """Initialize chunker.

        Args:
            max_tokens: Maximum tokens per chunk.
            overlap_tokens: Token overlap between chunks.
            preserve_sections: Try to keep markdown sections together.
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.preserve_sections = preserve_sections

        self.max_chars = max_tokens * self.CHARS_PER_TOKEN
        self.overlap_chars = overlap_tokens * self.CHARS_PER_TOKEN

    def chunk(
        self,
        content: str,
        metadata: Optional[dict] = None,
    ) -> list[DocumentChunk]:
        """Split content into chunks.

        Args:
            content: Document content (markdown preferred).
            metadata: Optional metadata to attach to chunks.

        Returns:
            List of document chunks.
        """
        if not content:
            return []

        metadata = metadata or {}

        if self.preserve_sections:
            chunks = self._chunk_by_sections(content, metadata)
        else:
            chunks = self._chunk_by_size(content, metadata)

        return chunks

    def _chunk_by_sections(self, content: str, metadata: dict) -> list[DocumentChunk]:
        """Chunk by markdown sections, splitting large sections."""
        chunks = []
        current_chunk = ""
        current_section = None

        # Split by markdown headers
        section_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        # Find all section boundaries
        sections = []
        last_end = 0

        for match in section_pattern.finditer(content):
            if last_end < match.start():
                # Content before this header
                sections.append((current_section, content[last_end : match.start()]))
            current_section = match.group(2).strip()
            last_end = match.end()

        # Add remaining content
        if last_end < len(content):
            sections.append((current_section, content[last_end:]))

        # Build chunks from sections
        for section_title, section_content in sections:
            section_content = section_content.strip()

            if not section_content:
                continue

            # Check if adding this section would exceed limit
            combined = current_chunk + "\n\n" + section_content if current_chunk else section_content
            combined_tokens = len(combined) // self.CHARS_PER_TOKEN

            if combined_tokens <= self.max_tokens:
                # Fits in current chunk
                current_chunk = combined
            else:
                # Doesn't fit - save current chunk and start new one
                if current_chunk:
                    chunks.append(
                        DocumentChunk(
                            content=current_chunk.strip(),
                            index=len(chunks),
                            token_count=len(current_chunk) // self.CHARS_PER_TOKEN,
                            section_title=section_title,
                            metadata=metadata.copy(),
                        )
                    )

                # Check if section itself is too large
                if len(section_content) > self.max_chars:
                    # Split large section by paragraphs
                    sub_chunks = self._split_large_section(section_content, section_title, metadata, len(chunks))
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section_content

        # Don't forget last chunk
        if current_chunk.strip():
            chunks.append(
                DocumentChunk(
                    content=current_chunk.strip(),
                    index=len(chunks),
                    token_count=len(current_chunk) // self.CHARS_PER_TOKEN,
                    metadata=metadata.copy(),
                )
            )

        # Add overlap context
        chunks = self._add_overlap(chunks)

        return chunks

    def _split_large_section(
        self,
        content: str,
        section_title: Optional[str],
        metadata: dict,
        start_index: int,
    ) -> list[DocumentChunk]:
        """Split a large section by paragraphs."""
        chunks = []
        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            combined = current_chunk + "\n\n" + para if current_chunk else para

            if len(combined) <= self.max_chars:
                current_chunk = combined
            else:
                if current_chunk:
                    chunks.append(
                        DocumentChunk(
                            content=current_chunk.strip(),
                            index=start_index + len(chunks),
                            token_count=len(current_chunk) // self.CHARS_PER_TOKEN,
                            section_title=section_title,
                            metadata=metadata.copy(),
                        )
                    )

                # If single paragraph is too large, split by sentences
                if len(para) > self.max_chars:
                    sub_chunks = self._split_by_sentences(para, section_title, metadata, start_index + len(chunks))
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk.strip():
            chunks.append(
                DocumentChunk(
                    content=current_chunk.strip(),
                    index=start_index + len(chunks),
                    token_count=len(current_chunk) // self.CHARS_PER_TOKEN,
                    section_title=section_title,
                    metadata=metadata.copy(),
                )
            )

        return chunks

    def _split_by_sentences(
        self,
        content: str,
        section_title: Optional[str],
        metadata: dict,
        start_index: int,
    ) -> list[DocumentChunk]:
        """Split by sentences as last resort."""
        chunks = []

        # Simple sentence splitting (handles most cases)
        sentences = re.split(r"(?<=[.!?])\s+", content)
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            combined = current_chunk + " " + sentence if current_chunk else sentence

            if len(combined) <= self.max_chars:
                current_chunk = combined
            else:
                if current_chunk:
                    chunks.append(
                        DocumentChunk(
                            content=current_chunk.strip(),
                            index=start_index + len(chunks),
                            token_count=len(current_chunk) // self.CHARS_PER_TOKEN,
                            section_title=section_title,
                            metadata=metadata.copy(),
                        )
                    )
                current_chunk = sentence

        if current_chunk.strip():
            chunks.append(
                DocumentChunk(
                    content=current_chunk.strip(),
                    index=start_index + len(chunks),
                    token_count=len(current_chunk) // self.CHARS_PER_TOKEN,
                    section_title=section_title,
                    metadata=metadata.copy(),
                )
            )

        return chunks

    def _chunk_by_size(self, content: str, metadata: dict) -> list[DocumentChunk]:
        """Simple chunking by character count."""
        chunks = []
        start = 0

        while start < len(content):
            end = start + self.max_chars

            # Try to break at paragraph or sentence boundary
            if end < len(content):
                # Look for paragraph break
                para_break = content.rfind("\n\n", start, end)
                if para_break > start + self.max_chars // 2:
                    end = para_break

                else:
                    # Look for sentence break
                    for punct in ".!?":
                        sent_break = content.rfind(punct, start, end)
                        if sent_break > start + self.max_chars // 2:
                            end = sent_break + 1
                            break

            chunk_content = content[start:end].strip()

            if chunk_content:
                chunks.append(
                    DocumentChunk(
                        content=chunk_content,
                        index=len(chunks),
                        token_count=len(chunk_content) // self.CHARS_PER_TOKEN,
                        metadata=metadata.copy(),
                    )
                )

            # Move start, accounting for overlap
            start = end - self.overlap_chars if end < len(content) else end

        return chunks

    def _add_overlap(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Add overlap context from previous chunk."""
        if len(chunks) <= 1 or self.overlap_chars == 0:
            return chunks

        for i in range(1, len(chunks)):
            prev_content = chunks[i - 1].content
            overlap_text = prev_content[-self.overlap_chars :] if len(prev_content) > self.overlap_chars else prev_content

            # Add as metadata rather than modifying content
            chunks[i].metadata["overlap_from_previous"] = overlap_text

        return chunks

    def estimate_tokens(self, content: str) -> int:
        """Estimate token count for content.

        Args:
            content: Text content.

        Returns:
            Estimated token count.
        """
        return len(content) // self.CHARS_PER_TOKEN
