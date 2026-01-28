"""Utilities for Supreme Court justice metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from civitas.db.models import Justice, JusticeOpinion

SCOTUS_BIO_URL = "https://www.supremecourt.gov/about/biographies.aspx"
SCOTUS_ABOUT_BASE = "https://www.supremecourt.gov/about/"

ACTIVE_JUSTICES = {
    "John G. Roberts",
    "Clarence Thomas",
    "Samuel A. Alito",
    "Sonia Sotomayor",
    "Elena Kagan",
    "Neil M. Gorsuch",
    "Brett M. Kavanaugh",
    "Amy Coney Barrett",
    "Ketanji Brown Jackson",
}

WIKIPEDIA_URLS = {
    "John G. Roberts": "https://en.wikipedia.org/wiki/John_G._Roberts",
    "Clarence Thomas": "https://en.wikipedia.org/wiki/Clarence_Thomas",
    "Samuel A. Alito": "https://en.wikipedia.org/wiki/Samuel_Alito",
    "Sonia Sotomayor": "https://en.wikipedia.org/wiki/Sonia_Sotomayor",
    "Elena Kagan": "https://en.wikipedia.org/wiki/Elena_Kagan",
    "Neil M. Gorsuch": "https://en.wikipedia.org/wiki/Neil_Gorsuch",
    "Brett M. Kavanaugh": "https://en.wikipedia.org/wiki/Brett_Kavanaugh",
    "Amy Coney Barrett": "https://en.wikipedia.org/wiki/Amy_Coney_Barrett",
    "Ketanji Brown Jackson": "https://en.wikipedia.org/wiki/Ketanji_Brown_Jackson",
    "Anthony M. Kennedy": "https://en.wikipedia.org/wiki/Anthony_Kennedy",
    "Stephen G. Breyer": "https://en.wikipedia.org/wiki/Stephen_Breyer",
}


@dataclass(frozen=True)
class JusticeMetadata:
    """Parsed metadata for a justice."""

    name: str
    role: str
    photo_url: str | None
    official_bio_url: str
    wikipedia_url: str | None
    is_active: bool


def _slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def _last_name(name: str) -> str:
    parts = [part for part in re.split(r"\s+", name) if part]
    return parts[-1] if parts else name


def fetch_justice_metadata() -> list[JusticeMetadata]:
    """Fetch justice names and photo URLs from supremecourt.gov."""
    response = httpx.get(
        SCOTUS_BIO_URL,
        timeout=20.0,
        headers={"User-Agent": "Civitas/1.0 (civic data project)"},
        follow_redirects=True,
    )
    response.raise_for_status()
    html = response.text

    pattern = re.compile(
        r'<img[^>]+src="([^"]*justice_pictures[^"]+)"[^>]*alt="([^"]+)"',
        re.IGNORECASE,
    )

    items: list[JusticeMetadata] = []
    for match in pattern.finditer(html):
        src = match.group(1)
        alt = match.group(2)

        name_part, role_part = _parse_alt_text(alt)
        if not name_part:
            continue

        photo_path = quote(src.strip())
        if not photo_path.startswith("http"):
            photo_path = photo_path.lstrip("/")
            photo_url = f"{SCOTUS_ABOUT_BASE}{photo_path}"
        else:
            photo_url = photo_path

        name = name_part.strip()
        is_active = name in ACTIVE_JUSTICES
        items.append(
            JusticeMetadata(
                name=name,
                role=role_part,
                photo_url=photo_url,
                official_bio_url=SCOTUS_BIO_URL,
                wikipedia_url=WIKIPEDIA_URLS.get(name),
                is_active=is_active,
            )
        )

    return items


def _parse_alt_text(alt_text: str) -> tuple[str | None, str]:
    if not alt_text:
        return None, ""
    parts = [part.strip() for part in alt_text.split(",", 1)]
    name = parts[0]
    role = parts[1] if len(parts) > 1 else ""
    return name, role


def sync_justices(session) -> int:
    """Sync justice metadata into the database."""
    items = fetch_justice_metadata()
    updated = 0

    for item in items:
        slug = _slugify_name(item.name)
        justice = session.query(Justice).filter(Justice.slug == slug).first()
        last = _last_name(item.name)

        if justice is None:
            justice = Justice(
                name=item.name,
                last_name=last,
                slug=slug,
                role=item.role,
                is_active=item.is_active,
                official_bio_url=item.official_bio_url,
                official_photo_url=item.photo_url,
                wikipedia_url=item.wikipedia_url,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(justice)
            updated += 1
            continue

        changed = False
        for field, value in (
            ("name", item.name),
            ("last_name", last),
            ("role", item.role),
            ("official_bio_url", item.official_bio_url),
            ("official_photo_url", item.photo_url),
            ("wikipedia_url", item.wikipedia_url),
            ("is_active", item.is_active),
        ):
            if getattr(justice, field) != value:
                setattr(justice, field, value)
                changed = True
        if changed:
            justice.updated_at = datetime.now(UTC)
            updated += 1

    return updated


def link_opinions_to_justices(session) -> int:
    """Attach justice IDs to opinions based on author names."""
    updated = 0
    justices = session.query(Justice).all()
    last_name_map = {justice.last_name.lower(): justice.id for justice in justices}

    for opinion in session.query(JusticeOpinion).filter(JusticeOpinion.justice_id.is_(None)):
        if not opinion.author_name:
            continue
        key = opinion.author_name.strip().lower()
        justice_id = last_name_map.get(key)
        if justice_id:
            opinion.justice_id = justice_id
            updated += 1

    return updated
