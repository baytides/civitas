"""Database models for legal citations.

Stores extracted citations linking documents to each other:
- Court cases citing other cases (case law network)
- Court cases citing legislation (statute interpretation)
- Legislation referencing other legislation
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from civitas.db.models import Base, utcnow


class Citation(Base):
    """A legal citation linking two documents.

    Citations create a network of legal documents:
    - Source: The document containing the citation
    - Target: The document being cited

    This enables analysis like:
    - Which statutes are most frequently challenged in court?
    - What cases cite a particular ruling?
    - How does case law evolve over time?
    """

    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Source document (where citation appears)
    source_type: Mapped[str] = mapped_column(String(20))  # "case", "legislation"
    source_id: Mapped[int] = mapped_column(Integer, index=True)

    # Target (what's being cited)
    target_type: Mapped[str] = mapped_column(String(20))  # "case", "legislation", "statute"
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK if resolved
    target_citation: Mapped[str] = mapped_column(String(200))  # Raw citation text

    # Citation metadata
    citation_type: Mapped[str] = mapped_column(String(50))  # "full", "short", "supra", "id"
    reporter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional metadata
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    court: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Context (surrounding text)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution status
    is_resolved: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_citation_source", "source_type", "source_id"),
        Index("ix_citation_target", "target_type", "target_id"),
        Index("ix_citation_reporter", "reporter", "volume", "page"),
    )
