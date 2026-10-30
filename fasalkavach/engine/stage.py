"""Work out which growth stage a crop is in from its sowing/transplanting date."""
from datetime import date

from .crops import CROPS


class StageError(ValueError):
    """Raised for inputs we cannot compute a stage for (bad date, season over...)."""


def get_crop_stage(crop: str, planted_on: str, today: date | None = None) -> dict:
    if crop not in CROPS:
        raise StageError(f"Unsupported crop '{crop}'. Supported: {', '.join(CROPS)}")
    info = CROPS[crop]
    today = today or date.today()

    try:
        planted = date.fromisoformat(planted_on)
    except (TypeError, ValueError):
        raise StageError(f"'{planted_on}' is not a valid date (expected YYYY-MM-DD)")

    days = (today - planted).days
    if days < 0:
        raise StageError(f"The {info['date_label']} {planted_on} is in the future")

    for name, start, end, sensitivity in info["stages"]:
        if start <= days < end:
            return {
                "crop": crop,
                "crop_label": info["label"],
                "stage": name,
                "days_since_planting": days,
                "stage_day_range": [start, end],
                "days_left_in_stage": end - days,
                "sensitivity": sensitivity,
                "source": info["source"],
            }

    last_end = info["stages"][-1][2]
    raise StageError(
        f"{info['label']} planted on {planted_on} is {days} days old - beyond the "
        f"{last_end}-day season, so it has probably been harvested already"
    )
