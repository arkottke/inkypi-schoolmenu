#!/usr/bin/env python3
"""Test script to fetch and display school menu."""

import re
from datetime import date, timedelta
from typing import Dict, List

import requests

DISTRICT_ID = "1212122355243477"
SITE_CODE = "894"
SITE_CODE_2 = "1237"

GQL_ENDPOINT = "https://api.isitesoftware.com/graphql"

def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())

COMMON_MENU_ITEM_FILTER = {
    "Garden Bar:",
    "organic fresh fruits and veggies",
    "straus organic 1% milk",
    "non-fat milk",
}
COMMON_MENU_ITEM_FILTER = {_normalize_name(item) for item in COMMON_MENU_ITEM_FILTER}

def _post_graphql(query: str) -> dict:
    headers = {"Content-Type": "application/json"}
    body = {"query": query}
    resp = requests.post(GQL_ENDPOINT, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(str(payload["errors"]))
    return payload.get("data", {})

def fetch_menu_items(
    district_id: str, site_id: str, menu_name: str, school_site_id: str = ""
) -> Dict[str, List[str]]:
    if school_site_id:
        site_input = "{" + f'depth_0_id:"{site_id}", depth_1_id:"{school_site_id}"' + "}"
    else:
        site_input = "{" + f'depth_0_id:"{site_id}"' + "}"

    query_menu_types = (
        "{"
        f'  menuTypes(site:{site_input}, publish_location:"website") {{ id name }}'
        "}"
    )
    mt_data = _post_graphql(query_menu_types)
    menu_types = mt_data.get("menuTypes") or []
    if not menu_types:
        raise ValueError(f"No menu types found for site {site_id}")

    target = _normalize_name(menu_name)
    exact = [mt for mt in menu_types if _normalize_name(mt.get("name", "")) == target]
    if len(exact) == 1:
        menu_type_id = exact[0]["id"]
    else:
        partial = [mt for mt in menu_types if target in _normalize_name(mt.get("name", ""))]
        if len(partial) == 1:
            menu_type_id = partial[0]["id"]
        elif not partial:
            raise ValueError(f"Menu '{menu_name}' not found. Available: {[mt.get('name') for mt in menu_types]}")
        else:
            raise ValueError(f"Ambiguous menu '{menu_name}'. Candidates: {[mt.get('name') for mt in partial]}")

    today = date.today()
    months_to_fetch = [(today.month - 1, today.year)]
    if today.day > 20:
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
        items = (mt_data.get("menu") or {}).get("items") or []

        for it in items:
            raw_month = it.get("month")
            month_num = (raw_month + 1) if isinstance(raw_month, int) else (m_idx + 1)
            item_year = it.get("year") or year_val
            try:
                day_int = int(it.get("day"))
            except (ValueError, TypeError):
                continue
            date_key = f"{item_year}-{month_num:02d}-{day_int:02d}"
            name = (it.get("product") or {}).get("name")
            if name and _normalize_name(name) not in COMMON_MENU_ITEM_FILTER:
                by_date.setdefault(date_key, []).append(name)

    return {k: by_date[k] for k in sorted(by_date) if by_date[k]}

def next_school_days(n: int):
    """Get next N weekdays starting from today."""
    out = []
    cur = date.today()
    while len(out) < n:
        if cur.weekday() < 5:  # Monday-Friday
            out.append(cur)
        cur += timedelta(days=1)
    return out

if __name__ == "__main__":
    print(f"Fetching menu for district={DISTRICT_ID}, site={SITE_CODE}, site2={SITE_CODE_2}")
    print()
    
    menu_items = fetch_menu_items(DISTRICT_ID, SITE_CODE, "Lunch Elementary Schools", SITE_CODE_2)
    
    target_days = next_school_days(3)
    
    for d in target_days:
        iso = d.isoformat()
        items = menu_items.get(iso, ["No menu available"])
        print(f"{d.strftime('%A, %B %d')}:")
        for item in items:
            print(f"  - {item}")
        print()
