"""SchoolMenu plugin (GraphQL based).

Identity of a specific published menu is determined by three required fields:
    site_id        (depth_0 site / district)
    menu_name      (human readable menu type, e.g. "Lunch Elementary Schools")
    site_child_id  (depth_1 site / school)

This implementation fetches the currently published month for the given menu
name and renders the next N school days using the Jinja template in
`render/menu.html` with associated CSS.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List

import requests

from plugins.base_plugin.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / Config
# ---------------------------------------------------------------------------
GQL_ENDPOINT = "https://api.isitesoftware.com/graphql"
FONT_SIZES: Dict[str, float] = {
    "x-small": 0.6,
    "smaller": 0.7,
    "small": 0.8,
    "normal": 1.0,
    "large": 1.2,
    "larger": 1.4,
    "x-large": 1.6,
}
MIN_DAYS = 1
MAX_DAYS = 5
PENDING_TEXT = "Not yet published"


# Items that are considered boilerplate / ubiquitous accompaniments and should
# be hidden from the rendered menu. These are matched on a normalized (lower
# case, collapsed whitespace) exact basis. Expand this list as needed.
def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


COMMON_MENU_ITEM_FILTER = {
    "Garden Bar:",
    "organic fresh fruits and veggies",
    "straus organic 1% milk",
    "non-fat milk",
}
COMMON_MENU_ITEM_FILTER = {_normalize_name(item) for item in COMMON_MENU_ITEM_FILTER}


# ---------------------------------------------------------------------------
# GraphQL helper (embedded minimal subset of previous graphql_menus.py)
# ---------------------------------------------------------------------------
class GraphQLError(RuntimeError):
    pass


def _post_graphql(query: str) -> dict:
    headers = {"Content-Type": "application/json"}
    body = {"query": query}
    resp = requests.post(GQL_ENDPOINT, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise GraphQLError(str(payload["errors"]))
    return payload.get("data", {})


def _validate_site_in_district(district_id: str, school_id: str) -> None:
    """Raise ValueError if the school_id is not part of the district.

    Uses a lightweight query that enumerates top-level sites for the org.
    """
    query = f'{{  organization(id:"{district_id}") {{ id sites {{ id name }} }}}}'
    data = _post_graphql(query).get("organization") or {}
    schools = data.get("sites") or []
    school_ids = {s.get("id") for s in schools}
    if school_id not in school_ids:
        raise ValueError(
            f"School id {school_id} not found in organization {district_id}. Available: {sorted(school_ids)}"
        )


def fetch_menu_items(
    district_id: str, site_id: str, menu_name: str, publish_location: str = "website"
) -> Dict[str, List[str]]:
    """Return mapping date -> list of product names for the current published month.

    Parameters
    ----------
    district_id: str
        ID of the district (e.g., 1212122355243477)
    site_id: str
        ID of the school (e.g., 894)
    menu_name : str
        Human-readable menu name (e.g. "Lunch Elementary Schools").
    publish_location : str
        The location where the menu is published (e.g. "website").

    Returns
    -------
    dict[str, list[str]]
        ISO date (YYYY-MM-DD) keys in chronological order, each value a list of item names.
    """
    if district_id:
        _validate_site_in_district(district_id, site_id)

    site_input = "{" + f'depth_0_id:"{site_id}"' + "}"

    # 1. Fetch menuTypes for site to resolve name -> menuType id
    query_menu_types = (
        "{"
        f'  menuTypes(site:{site_input}, publish_location:"{publish_location}") {{ id name }}'
        "}"
    )
    mt_data = _post_graphql(query_menu_types)
    menu_types = mt_data.get("menuTypes") or []
    if not menu_types:
        raise ValueError("No menuTypes returned for site; cannot resolve menu name.")

    target = _normalize_name(menu_name)
    exact = [mt for mt in menu_types if _normalize_name(mt.get("name", "")) == target]
    if len(exact) == 1:
        menu_type_id = exact[0]["id"]
    elif len(exact) > 1:
        raise ValueError(f"Ambiguous menu name '{menu_name}' (multiple exact matches)")
    else:
        partial = [
            mt for mt in menu_types if target in _normalize_name(mt.get("name", ""))
        ]
        if len(partial) == 1:
            menu_type_id = partial[0]["id"]
        elif not partial:
            raise ValueError(
                f"Menu name '{menu_name}' not found. Available: {[mt.get('name') for mt in menu_types]}"
            )
        else:
            raise ValueError(
                f"Ambiguous menu name '{menu_name}'. Candidates: {[mt.get('name') for mt in partial]}"
            )

    # 2. Fetch menu items for current (and possibly next) month
    # We bypass defaultPublishedMonth to ensure we get the relevant dates.
    today = date.today()
    # 0-indexed month for GraphQL
    months_to_fetch = [(today.month - 1, today.year)]

    # If late in the month, fetch next month too to ensure coverage
    if today.day > 20:
        # Calculate next month safely
        if today.month == 12:
            months_to_fetch.append((0, today.year + 1))
        else:
            months_to_fetch.append((today.month, today.year))

    by_date: Dict[str, List[str]] = {}

    for m_idx, year_val in months_to_fetch:
        query_menu = (
            "{"
            f'  menuType(id:"{menu_type_id}") {{ menu(month:{m_idx}, year:{year_val}) {{ items {{ day month year product {{ name }} }} }} }}'
            "}"
        )
        mt_data = _post_graphql(query_menu).get("menuType") or {}
        menu_payload = mt_data.get("menu") or {}
        items = menu_payload.get("items") or []

        for it in items:
            # Month resolution
            raw_item_month = it.get("month")
            if isinstance(raw_item_month, int):
                month_num = raw_item_month + 1
            else:
                month_num = m_idx + 1

            item_year = it.get("year") or year_val

            day_raw = it.get("day")
            try:
                day_int = int(day_raw)
            except (ValueError, TypeError):
                continue

            date_key = f"{item_year}-{month_num:02d}-{day_int:02d}"
            prod = it.get("product") or {}
            name = prod.get("name")
            if not name:
                continue
            # Filter out ubiquitous / condiment / generic sides defined above
            norm_name = _normalize_name(name)
            if norm_name in COMMON_MENU_ITEM_FILTER:
                continue
            by_date.setdefault(date_key, []).append(name)

    # Ensure chronological ordering (Python preserves insertion order)
    ordered: Dict[str, List[str]] = {}
    for k in sorted(by_date):
        ordered[k] = by_date[k]
    # Drop any dates that became empty after filtering
    filtered = {k: v for k, v in ordered.items() if v}
    return filtered


# ---------------------------------------------------------------------------
# Data structures / helpers
# ---------------------------------------------------------------------------
@dataclass
class ParsedSettings:
    district_id: str
    school_id: str
    menu_name: str
    days: int
    title: str
    show_date: bool
    font_scale: float
    primary_color: str
    text_color: str
    background_color: str
    show_timestamp: bool


class SchoolMenu(BasePlugin):
    def generate_settings_template(self):  # type: ignore[override]
        params = super().generate_settings_template()
        params["style_settings"] = "True"
        return params

    # ---------------------------------------------------------------------
    # Public entry
    # ---------------------------------------------------------------------
    def generate_image(self, settings, device_config):  # type: ignore[override]
        cfg = self._parse_settings(settings)
        logger.debug("Parsed settings: %s", cfg)

        # Fetch menu data via GraphQL. If it fails, fallback to placeholder.
        fetch_ok = True
        try:
            # Order: district_id, school_id, menu_name (positional to avoid duplication)
            logger.info(
                f"Fetching menu: district={cfg.district_id}, school={cfg.school_id}, menu={cfg.menu_name}"
            )
            all_items = fetch_menu_items(
                cfg.district_id,
                cfg.school_id,
                cfg.menu_name,
            )
            logger.info(f"Successfully fetched {len(all_items)} dates from GraphQL")
        except Exception as e:  # pragma: no cover
            fetch_ok = False
            logger.error(
                f"GraphQL fetch failed: {type(e).__name__}: {e}", exc_info=True
            )
            today_iso = date.today().isoformat()
            all_items = {today_iso: ["Menu not available"]}

        # Filter upcoming school days
        target_days = self._next_school_days(cfg.days)
        menu_subset: Dict[str, List[str]] = {}
        for d in target_days:
            iso = d.isoformat()
            if iso in all_items:
                menu_subset[iso] = all_items[iso]
            else:
                # If fetch succeeded but this specific future day has no data, use pending placeholder
                if fetch_ok and d >= date.today():
                    menu_subset[iso] = [PENDING_TEXT]
                else:
                    menu_subset[iso] = []

        # Build template parameters
        tz_now = datetime.now()
        day_names = {
            iso: datetime.fromisoformat(iso).strftime("%A") for iso in menu_subset
        }
        formatted_dates = {
            iso: datetime.fromisoformat(iso).strftime("%b %d") for iso in menu_subset
        }
        single_date_text = ""  # Only used when one day and show_date
        if len(menu_subset) == 1:
            only_iso = next(iter(menu_subset))
            single_date_text = datetime.fromisoformat(only_iso).strftime("%A, %B %d")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params = {
            "plugin_settings": {
                **settings,
                "customTitle": cfg.menu_name,
                "showDate": "true" if cfg.show_date else "false",
                "primaryColor": cfg.primary_color,
                "textColor": cfg.text_color,
                "backgroundColor": cfg.background_color,
            },
            "menu_data": menu_subset,
            "day_names": day_names,
            "formatted_dates": formatted_dates,
            "single_date_text": single_date_text,
            "today_str": date.today().isoformat(),
            "timestamp": tz_now.strftime("%Y-%m-%d %H:%M"),
            "show_timestamp": cfg.show_timestamp,
            "font_scale": cfg.font_scale,
        }

        image = self.render_image(dimensions, "menu.html", "menu.css", template_params)
        if not image:
            raise RuntimeError("Failed to render SchoolMenu image.")
        return image

    # ------------------------------------------------------------------
    # Parsing / filtering
    # ------------------------------------------------------------------
    def _parse_settings(self, settings: dict) -> ParsedSettings:
        district_id = settings.get("districtId", "").strip()
        if not district_id:
            raise ValueError("districtId is required")

        school_id = settings.get("schoolId", "").strip()
        if not school_id:
            raise ValueError("schoolId is required")

        menu_name = settings.get("menuName", "").strip()
        if not menu_name:
            raise ValueError("menuName is required")

        try:
            days = int(settings.get("numDays", 3))
        except Exception:
            days = 3
        if not (MIN_DAYS <= days <= MAX_DAYS):
            days = 3
        show_date = str(settings.get("showDate", "true")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        title = settings.get("customTitle", "School Lunch Menu").strip()

        font_scale = FONT_SIZES.get(settings.get("fontSize", "normal"), 1.0)
        primary_color = settings.get("primaryColor", "#323296")
        text_color = settings.get("textColor", "#000000")
        background_color = settings.get("backgroundColor", "#ffffff")
        show_timestamp = str(
            settings.get("showTimestamp", settings.get("displayRefreshTime", "true"))
        ).lower() in {"1", "true", "yes", "on"}
        return ParsedSettings(
            district_id=district_id,
            school_id=school_id,
            menu_name=menu_name,
            days=days,
            title=title,
            show_date=show_date,
            font_scale=font_scale,
            primary_color=primary_color,
            text_color=text_color,
            background_color=background_color,
            show_timestamp=show_timestamp,
        )

    def _next_school_days(self, n: int) -> List[date]:
        out: List[date] = []
        cur = date.today()
        while len(out) < n:
            if cur.weekday() < 5:  # Monday-Friday
                out.append(cur)
            cur += timedelta(days=1)
        return out


__all__ = ["SchoolMenu"]
