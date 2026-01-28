"""Supreme Court justices API endpoints."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from civitas.api.schemas import JusticeBase, JusticeDetail, JusticeList
from civitas.db.models import Justice, JusticeOpinion, JusticeProfile

router = APIRouter()

PHOTO_DIR = Path("data/justices/photos")


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _parse_json_object(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _photo_url(request: Request, slug: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/justices/{slug}/photo"


def _ensure_photo_dir() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)


def _guess_extension(url: str) -> str:
    lowered = url.lower()
    if lowered.endswith(".png"):
        return "png"
    if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
        return "jpg"
    return "jpg"


def _download_photo(url: str, path: Path) -> bool:
    try:
        response = httpx.get(
            url,
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "Civitas/1.0 (civic data project)"},
        )
        if response.status_code != 200:
            return False
        path.write_bytes(response.content)
        return True
    except Exception:
        return False


@router.get("/justices", response_model=JusticeList)
async def list_justices(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
) -> JusticeList:
    """List Supreme Court justices."""
    query = db.query(Justice)
    if active_only:
        query = query.filter(Justice.is_active.is_(True))

    total = query.count()
    offset = (page - 1) * per_page
    items = (
        query.order_by(Justice.is_active.desc(), Justice.last_name.asc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    items_out = []
    for item in items:
        base = JusticeBase.model_validate(item)
        payload = base.model_dump()
        payload["official_photo_url"] = _photo_url(request, item.slug)
        items_out.append(JusticeBase(**payload))

    return JusticeList(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
        items=items_out,
    )


@router.get("/justices/{slug}", response_model=JusticeDetail)
async def get_justice(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JusticeDetail:
    """Get a justice by slug with profile data."""
    justice = db.query(Justice).filter(Justice.slug == slug).first()
    if not justice:
        raise HTTPException(status_code=404, detail="Justice not found")

    profile = db.query(JusticeProfile).filter(JusticeProfile.justice_id == justice.id).first()

    counts = {
        "majority": db.query(JusticeOpinion)
        .filter(
            JusticeOpinion.justice_id == justice.id,
            JusticeOpinion.opinion_type == "majority",
        )
        .count(),
        "dissent": db.query(JusticeOpinion)
        .filter(
            JusticeOpinion.justice_id == justice.id,
            JusticeOpinion.opinion_type == "dissent",
        )
        .count(),
        "concurrence": db.query(JusticeOpinion)
        .filter(
            JusticeOpinion.justice_id == justice.id,
            JusticeOpinion.opinion_type == "concurrence",
        )
        .count(),
    }
    counts["total"] = counts["majority"] + counts["dissent"] + counts["concurrence"]

    base = JusticeBase.model_validate(justice)
    payload = base.model_dump()
    payload["official_photo_url"] = _photo_url(request, justice.slug)

    return JusticeDetail(
        **payload,
        appointed_by=justice.appointed_by,
        official_bio_url=justice.official_bio_url,
        wikipedia_url=justice.wikipedia_url,
        opinion_counts=counts,
        profile_summary=profile.profile_summary if profile else None,
        judicial_philosophy=profile.judicial_philosophy if profile else None,
        voting_tendencies=_parse_json_list(profile.voting_tendencies) if profile else [],
        notable_opinions=_parse_json_list(profile.notable_opinions) if profile else [],
        statistical_profile=_parse_json_object(profile.statistical_profile) if profile else {},
        methodology=profile.methodology if profile else None,
        disclaimer=profile.disclaimer if profile else None,
        generated_at=profile.generated_at if profile else None,
    )


@router.get("/justices/{slug}/photo")
async def get_justice_photo(
    slug: str,
    db: Session = Depends(get_db),
) -> Response:
    """Serve cached justice photo, downloading once if needed."""
    justice = db.query(Justice).filter(Justice.slug == slug).first()
    if not justice or not justice.official_photo_url:
        raise HTTPException(status_code=404, detail="Photo not found")

    _ensure_photo_dir()
    ext = _guess_extension(justice.official_photo_url)
    photo_path = PHOTO_DIR / f"{slug}.{ext}"

    if not photo_path.exists():
        if not _download_photo(justice.official_photo_url, photo_path):
            raise HTTPException(status_code=404, detail="Photo not available")

    media_type, _ = mimetypes.guess_type(str(photo_path))
    return FileResponse(photo_path, media_type=media_type or "image/jpeg")
