"""Analytics router — aggregate brew statistics and cross-bean recipe comparison."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.routers.beans import _get_active_bean

router = APIRouter(prefix="/analytics", tags=["analytics"])
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_stats(db: Session) -> dict:
    """Compute aggregate statistics across all beans/measurements."""
    all_measurements = db.query(Measurement).all()
    total_shots = len(all_measurements)

    if total_shots == 0:
        return {
            "total_shots": 0,
            "total_beans": 0,
            "avg_taste": None,
            "best_taste": None,
            "best_bean_name": None,
            "total_failed": 0,
            "improvement_rate": "—",
        }

    non_failed = [m for m in all_measurements if not m.is_failed]
    failed = [m for m in all_measurements if m.is_failed]

    # Distinct beans that have at least 1 measurement
    bean_ids_with_measurements = {m.bean_id for m in all_measurements}
    total_beans = len(bean_ids_with_measurements)

    total_failed = len(failed)

    # Average taste (excluding failed)
    avg_taste = None
    if non_failed:
        avg_taste = round(sum(m.taste for m in non_failed) / len(non_failed), 1)

    # Best taste ever (excluding failed)
    best_taste = None
    best_bean_name = None
    if non_failed:
        best_m = max(non_failed, key=lambda m: m.taste)
        best_taste = best_m.taste
        # Look up bean name
        bean = db.query(Bean).filter(Bean.id == best_m.bean_id).first()
        best_bean_name = bean.name if bean else "Unknown"

    # Improvement rate: compare avg taste of first 10 vs last 10 non-failed shots
    # sorted by creation time
    improvement_rate = "—"
    non_failed_sorted = sorted(non_failed, key=lambda m: m.created_at)
    if len(non_failed_sorted) >= 10:
        first_10 = non_failed_sorted[:10]
        last_10 = non_failed_sorted[-10:]
        avg_first = sum(m.taste for m in first_10) / len(first_10)
        avg_last = sum(m.taste for m in last_10) / len(last_10)
        diff = round(avg_last - avg_first, 1)
        if diff > 0:
            improvement_rate = f"↑ {diff}"
        elif diff < 0:
            improvement_rate = f"↓ {abs(diff)}"
        else:
            improvement_rate = "→ 0.0"

    return {
        "total_shots": total_shots,
        "total_beans": total_beans,
        "avg_taste": avg_taste,
        "best_taste": best_taste,
        "best_bean_name": best_bean_name,
        "total_failed": total_failed,
        "improvement_rate": improvement_rate,
    }


def _compute_comparison(db: Session) -> list[dict]:
    """Get the best (highest taste) non-failed recipe for each bean.

    Returns list of dicts sorted by taste descending.
    """
    beans = db.query(Bean).all()
    comparison = []

    for bean in beans:
        non_failed = (
            db.query(Measurement)
            .filter(Measurement.bean_id == bean.id, Measurement.is_failed.is_(False))
            .all()
        )
        if not non_failed:
            continue

        best = max(non_failed, key=lambda m: m.taste)
        shot_count = len(db.query(Measurement).filter(Measurement.bean_id == bean.id).all())

        comparison.append(
            {
                "bean_name": bean.name,
                "taste": best.taste,
                "grind_setting": best.grind_setting,
                "temperature": best.temperature,
                "preinfusion_pressure_pct": best.preinfusion_pressure_pct,
                "dose_in": best.dose_in,
                "target_yield": best.target_yield,
                "saturation": best.saturation,
                "shot_count": shot_count,
            }
        )

    # Sort by taste descending (best bean first)
    comparison.sort(key=lambda x: x["taste"], reverse=True)
    return comparison


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
async def analytics_page(request: Request, db: Session = Depends(get_db)):
    """Analytics page — aggregate brew stats and cross-bean comparison."""
    active_bean = _get_active_bean(request, db)
    stats = _compute_stats(db)
    comparison = _compute_comparison(db)

    return templates.TemplateResponse(
        request,
        "analytics/index.html",
        {
            "active_bean": active_bean,
            "stats": stats,
            "comparison": comparison,
        },
    )
