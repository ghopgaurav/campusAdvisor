"""
Cost of living tool for US university cities.

Uses a hardcoded baseline dataset (~40 major university cities) with
2024-2025 estimates. Fast, no API key, no network call.
For cities not in the dataset, returns national averages and suggests
using web_search for current data.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# City dataset — monthly costs in USD, 2024-2025 estimates
# ---------------------------------------------------------------------------

_CITY_DATA: dict[str, dict[str, Any]] = {
    "new york, ny": {
        "city": "New York", "state": "NY", "metro": "NYC Metro",
        "rent_1br": 2800, "rent_2br": 3800,
        "groceries": 450, "transport": 130, "utilities": 150,
        "phone_internet": 100, "health_insurance": 200,
        "total_monthly_estimate": 3830,
        "notes": "Manhattan prices much higher. Brooklyn/Queens more affordable. Excellent public transit.",
        "walkability": "Very High", "transit_quality": "Excellent",
    },
    "boston, ma": {
        "city": "Boston", "state": "MA", "metro": "Boston Metro",
        "rent_1br": 2400, "rent_2br": 3200,
        "groceries": 400, "transport": 90, "utilities": 140,
        "phone_internet": 95, "health_insurance": 200,
        "total_monthly_estimate": 3325,
        "notes": "Cambridge/Somerville popular with students. Good transit (MBTA). Cold winters raise utility bills.",
        "walkability": "High", "transit_quality": "Good",
    },
    "cambridge, ma": {
        "city": "Cambridge", "state": "MA", "metro": "Boston Metro",
        "rent_1br": 2600, "rent_2br": 3400,
        "groceries": 400, "transport": 90, "utilities": 140,
        "phone_internet": 95, "health_insurance": 200,
        "total_monthly_estimate": 3525,
        "notes": "Home to MIT and Harvard. Slightly pricier than Boston proper. Walkable to both campuses.",
        "walkability": "Very High", "transit_quality": "Excellent",
    },
    "san francisco, ca": {
        "city": "San Francisco", "state": "CA", "metro": "SF Bay Area",
        "rent_1br": 2900, "rent_2br": 3900,
        "groceries": 450, "transport": 100, "utilities": 130,
        "phone_internet": 95, "health_insurance": 200,
        "total_monthly_estimate": 3875,
        "notes": "Very expensive. Many students live in East Bay (Oakland/Berkeley) for lower rent. BART connects major areas.",
        "walkability": "High", "transit_quality": "Good",
    },
    "palo alto, ca": {
        "city": "Palo Alto", "state": "CA", "metro": "SF Bay Area",
        "rent_1br": 2700, "rent_2br": 3700,
        "groceries": 430, "transport": 80, "utilities": 120,
        "phone_internet": 95, "health_insurance": 200,
        "total_monthly_estimate": 3625,
        "notes": "Home to Stanford. Very expensive suburb. Car recommended or Caltrain to SF. No state income tax advantage — CA taxes still apply.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "los angeles, ca": {
        "city": "Los Angeles", "state": "CA", "metro": "LA Metro",
        "rent_1br": 2100, "rent_2br": 2900,
        "groceries": 400, "transport": 100, "utilities": 120,
        "phone_internet": 90, "health_insurance": 200,
        "total_monthly_estimate": 3010,
        "notes": "Car almost essential. Rent varies hugely by neighborhood (Westwood near UCLA vs Compton). LA Metro expanding.",
        "walkability": "Low", "transit_quality": "Fair",
    },
    "pasadena, ca": {
        "city": "Pasadena", "state": "CA", "metro": "LA Metro",
        "rent_1br": 1900, "rent_2br": 2600,
        "groceries": 380, "transport": 90, "utilities": 115,
        "phone_internet": 90, "health_insurance": 200,
        "total_monthly_estimate": 2775,
        "notes": "Home to Caltech. More affordable than LA proper. Metro Gold Line connects to downtown LA.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "san diego, ca": {
        "city": "San Diego", "state": "CA", "metro": "San Diego Metro",
        "rent_1br": 2000, "rent_2br": 2700,
        "groceries": 390, "transport": 75, "utilities": 110,
        "phone_internet": 90, "health_insurance": 200,
        "total_monthly_estimate": 2865,
        "notes": "Milder cost than SF/LA. Great weather. Car helpful outside UCSD campus area.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "irvine, ca": {
        "city": "Irvine", "state": "CA", "metro": "Orange County",
        "rent_1br": 2100, "rent_2br": 2800,
        "groceries": 380, "transport": 70, "utilities": 110,
        "phone_internet": 90, "health_insurance": 200,
        "total_monthly_estimate": 2950,
        "notes": "Home to UC Irvine. Planned city, very safe. Car essentially required.",
        "walkability": "Low", "transit_quality": "Poor",
    },
    "davis, ca": {
        "city": "Davis", "state": "CA", "metro": "Sacramento Metro",
        "rent_1br": 1500, "rent_2br": 1900,
        "groceries": 340, "transport": 40, "utilities": 100,
        "phone_internet": 80, "health_insurance": 180,
        "total_monthly_estimate": 2240,
        "notes": "Home to UC Davis. Extremely bike-friendly. Very affordable by CA standards.",
        "walkability": "High", "transit_quality": "Good",
    },
    "santa barbara, ca": {
        "city": "Santa Barbara", "state": "CA", "metro": "Santa Barbara",
        "rent_1br": 2000, "rent_2br": 2800,
        "groceries": 390, "transport": 65, "utilities": 110,
        "phone_internet": 85, "health_insurance": 190,
        "total_monthly_estimate": 2840,
        "notes": "Home to UCSB. Beautiful but expensive. Bike-friendly near campus (Isla Vista).",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "seattle, wa": {
        "city": "Seattle", "state": "WA", "metro": "Seattle Metro",
        "rent_1br": 1900, "rent_2br": 2600,
        "groceries": 400, "transport": 100, "utilities": 100,
        "phone_internet": 90, "health_insurance": 190,
        "total_monthly_estimate": 2780,
        "notes": "No state income tax. Tech hub so competition for housing is stiff. Good Link Light Rail.",
        "walkability": "High", "transit_quality": "Good",
    },
    "chicago, il": {
        "city": "Chicago", "state": "IL", "metro": "Chicago Metro",
        "rent_1br": 1700, "rent_2br": 2300,
        "groceries": 380, "transport": 105, "utilities": 130,
        "phone_internet": 90, "health_insurance": 190,
        "total_monthly_estimate": 2595,
        "notes": "Great public transit (CTA L). Very affordable relative to cost. Cold winters — higher winter utility bills.",
        "walkability": "High", "transit_quality": "Excellent",
    },
    "philadelphia, pa": {
        "city": "Philadelphia", "state": "PA", "metro": "Philadelphia Metro",
        "rent_1br": 1500, "rent_2br": 2000,
        "groceries": 360, "transport": 100, "utilities": 130,
        "phone_internet": 85, "health_insurance": 185,
        "total_monthly_estimate": 2360,
        "notes": "SEPTA subway/bus system. University City neighborhood (Penn, Drexel) very student-friendly.",
        "walkability": "High", "transit_quality": "Good",
    },
    "pittsburgh, pa": {
        "city": "Pittsburgh", "state": "PA", "metro": "Pittsburgh Metro",
        "rent_1br": 1200, "rent_2br": 1500,
        "groceries": 350, "transport": 80, "utilities": 120,
        "phone_internet": 85, "health_insurance": 180,
        "total_monthly_estimate": 2015,
        "notes": "Very affordable for a major university city. Bus system decent near CMU/Pitt campuses. Revitalized downtown.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "state college, pa": {
        "city": "State College", "state": "PA", "metro": "State College",
        "rent_1br": 950, "rent_2br": 1250,
        "groceries": 310, "transport": 30, "utilities": 110,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1650,
        "notes": "Home to Penn State. Very affordable college town. Car recommended for off-campus.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "atlanta, ga": {
        "city": "Atlanta", "state": "GA", "metro": "Atlanta Metro",
        "rent_1br": 1600, "rent_2br": 2100,
        "groceries": 360, "transport": 95, "utilities": 130,
        "phone_internet": 85, "health_insurance": 185,
        "total_monthly_estimate": 2455,
        "notes": "Home to Georgia Tech, Emory. Car very helpful outside Midtown. MARTA rail connects key areas.",
        "walkability": "Low", "transit_quality": "Fair",
    },
    "austin, tx": {
        "city": "Austin", "state": "TX", "metro": "Austin Metro",
        "rent_1br": 1500, "rent_2br": 2000,
        "groceries": 370, "transport": 90, "utilities": 140,
        "phone_internet": 85, "health_insurance": 180,
        "total_monthly_estimate": 2365,
        "notes": "Growing rapidly — prices rose steeply 2020-2023, stabilizing now. No state income tax. Car helpful.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "houston, tx": {
        "city": "Houston", "state": "TX", "metro": "Houston Metro",
        "rent_1br": 1200, "rent_2br": 1600,
        "groceries": 350, "transport": 80, "utilities": 135,
        "phone_internet": 80, "health_insurance": 175,
        "total_monthly_estimate": 2020,
        "notes": "No state income tax. Car essentially required. Very spread out city. Affordable housing.",
        "walkability": "Low", "transit_quality": "Poor",
    },
    "dallas, tx": {
        "city": "Dallas", "state": "TX", "metro": "DFW Metro",
        "rent_1br": 1300, "rent_2br": 1750,
        "groceries": 350, "transport": 80, "utilities": 140,
        "phone_internet": 80, "health_insurance": 175,
        "total_monthly_estimate": 2125,
        "notes": "No state income tax. DART light rail usable. Car largely necessary. Affordable overall.",
        "walkability": "Low", "transit_quality": "Fair",
    },
    "college station, tx": {
        "city": "College Station", "state": "TX", "metro": "Bryan-College Station",
        "rent_1br": 900, "rent_2br": 1200,
        "groceries": 300, "transport": 30, "utilities": 120,
        "phone_internet": 75, "health_insurance": 170,
        "total_monthly_estimate": 1595,
        "notes": "Home to Texas A&M. Extremely affordable. Car recommended. Classic college town.",
        "walkability": "Low", "transit_quality": "Poor",
    },
    "ann arbor, mi": {
        "city": "Ann Arbor", "state": "MI", "metro": "Ann Arbor Metro",
        "rent_1br": 1300, "rent_2br": 1800,
        "groceries": 340, "transport": 60, "utilities": 130,
        "phone_internet": 80, "health_insurance": 180,
        "total_monthly_estimate": 2090,
        "notes": "Home to University of Michigan. Walkable college town. TheRide bus system covers campus well.",
        "walkability": "High", "transit_quality": "Good",
    },
    "champaign, il": {
        "city": "Champaign", "state": "IL", "metro": "Champaign-Urbana",
        "rent_1br": 950, "rent_2br": 1250,
        "groceries": 310, "transport": 35, "utilities": 120,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1665,
        "notes": "Home to UIUC. Very affordable Midwest college town. MTD bus system is excellent on campus.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "west lafayette, in": {
        "city": "West Lafayette", "state": "IN", "metro": "Lafayette Metro",
        "rent_1br": 850, "rent_2br": 1100,
        "groceries": 290, "transport": 25, "utilities": 115,
        "phone_internet": 70, "health_insurance": 170,
        "total_monthly_estimate": 1520,
        "notes": "Home to Purdue. One of the most affordable major university towns. Car helpful off-campus.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "columbus, oh": {
        "city": "Columbus", "state": "OH", "metro": "Columbus Metro",
        "rent_1br": 1050, "rent_2br": 1400,
        "groceries": 320, "transport": 60, "utilities": 120,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1800,
        "notes": "Home to Ohio State. Affordable, growing city. Car helpful but campus area walkable.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "madison, wi": {
        "city": "Madison", "state": "WI", "metro": "Madison Metro",
        "rent_1br": 1100, "rent_2br": 1500,
        "groceries": 330, "transport": 55, "utilities": 115,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1850,
        "notes": "Home to UW-Madison. Vibrant college town. Very bikeable. Cold winters.",
        "walkability": "High", "transit_quality": "Good",
    },
    "minneapolis, mn": {
        "city": "Minneapolis", "state": "MN", "metro": "Twin Cities",
        "rent_1br": 1200, "rent_2br": 1650,
        "groceries": 340, "transport": 95, "utilities": 130,
        "phone_internet": 80, "health_insurance": 180,
        "total_monthly_estimate": 2025,
        "notes": "Home to UMN. Light rail (Green/Blue line) useful. Very cold winters — budget for heating.",
        "walkability": "High", "transit_quality": "Good",
    },
    "washington, dc": {
        "city": "Washington", "state": "DC", "metro": "DC Metro",
        "rent_1br": 2100, "rent_2br": 2900,
        "groceries": 410, "transport": 100, "utilities": 130,
        "phone_internet": 90, "health_insurance": 195,
        "total_monthly_estimate": 3025,
        "notes": "Home to Georgetown, GWU, American. Excellent Metro system. Maryland/Virginia suburbs cheaper.",
        "walkability": "Very High", "transit_quality": "Excellent",
    },
    "baltimore, md": {
        "city": "Baltimore", "state": "MD", "metro": "Baltimore Metro",
        "rent_1br": 1350, "rent_2br": 1850,
        "groceries": 350, "transport": 80, "utilities": 125,
        "phone_internet": 80, "health_insurance": 185,
        "total_monthly_estimate": 2170,
        "notes": "Home to Johns Hopkins. Light Rail/Metro connects to DC. Research Hill area popular with Hopkins students.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "new haven, ct": {
        "city": "New Haven", "state": "CT", "metro": "New Haven Metro",
        "rent_1br": 1500, "rent_2br": 2000,
        "groceries": 370, "transport": 65, "utilities": 140,
        "phone_internet": 85, "health_insurance": 190,
        "total_monthly_estimate": 2350,
        "notes": "Home to Yale. More affordable than NYC/Boston. CT Transit buses. Train to NYC in 2hrs.",
        "walkability": "High", "transit_quality": "Fair",
    },
    "princeton, nj": {
        "city": "Princeton", "state": "NJ", "metro": "Princeton Metro",
        "rent_1br": 1800, "rent_2br": 2400,
        "groceries": 390, "transport": 75, "utilities": 140,
        "phone_internet": 90, "health_insurance": 195,
        "total_monthly_estimate": 2690,
        "notes": "Home to Princeton University. Expensive suburb. NJ Transit to NYC/Philly. Very walkable downtown.",
        "walkability": "High", "transit_quality": "Good",
    },
    "ithaca, ny": {
        "city": "Ithaca", "state": "NY", "metro": "Ithaca Metro",
        "rent_1br": 1400, "rent_2br": 1900,
        "groceries": 360, "transport": 50, "utilities": 130,
        "phone_internet": 80, "health_insurance": 185,
        "total_monthly_estimate": 2205,
        "notes": "Home to Cornell. Steep hills require good shoes or bike. TCAT bus is free for Cornell students.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "amherst, ma": {
        "city": "Amherst", "state": "MA", "metro": "Pioneer Valley",
        "rent_1br": 1300, "rent_2br": 1750,
        "groceries": 340, "transport": 45, "utilities": 130,
        "phone_internet": 80, "health_insurance": 185,
        "total_monthly_estimate": 2080,
        "notes": "Home to UMass Amherst. Pioneer Valley Transit free for UMass students. Rural setting.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "raleigh, nc": {
        "city": "Raleigh", "state": "NC", "metro": "Research Triangle",
        "rent_1br": 1350, "rent_2br": 1800,
        "groceries": 340, "transport": 65, "utilities": 120,
        "phone_internet": 80, "health_insurance": 180,
        "total_monthly_estimate": 2135,
        "notes": "Research Triangle (NC State, Duke, UNC). Growing tech hub. Car generally needed.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "durham, nc": {
        "city": "Durham", "state": "NC", "metro": "Research Triangle",
        "rent_1br": 1400, "rent_2br": 1850,
        "groceries": 340, "transport": 65, "utilities": 120,
        "phone_internet": 80, "health_insurance": 180,
        "total_monthly_estimate": 2185,
        "notes": "Home to Duke. Triangle area growing rapidly. GoTriangle bus connects Research Triangle.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "denver, co": {
        "city": "Denver", "state": "CO", "metro": "Denver Metro",
        "rent_1br": 1600, "rent_2br": 2150,
        "groceries": 370, "transport": 100, "utilities": 110,
        "phone_internet": 85, "health_insurance": 185,
        "total_monthly_estimate": 2450,
        "notes": "RTD light rail system solid. Growing city. Outdoor access premium. Housing costs rose sharply post-2020.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "salt lake city, ut": {
        "city": "Salt Lake City", "state": "UT", "metro": "Salt Lake Metro",
        "rent_1br": 1200, "rent_2br": 1600,
        "groceries": 330, "transport": 70, "utilities": 105,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1955,
        "notes": "Home to University of Utah. TRAX light rail good for campus area. Outdoor paradise nearby.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "tempe, az": {
        "city": "Tempe", "state": "AZ", "metro": "Phoenix Metro",
        "rent_1br": 1300, "rent_2br": 1750,
        "groceries": 340, "transport": 65, "utilities": 150,
        "phone_internet": 80, "health_insurance": 180,
        "total_monthly_estimate": 2115,
        "notes": "Home to ASU. Valley Metro Light Rail connects Tempe to Phoenix/Mesa. High summer AC bills.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "tucson, az": {
        "city": "Tucson", "state": "AZ", "metro": "Tucson Metro",
        "rent_1br": 1000, "rent_2br": 1350,
        "groceries": 310, "transport": 45, "utilities": 140,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1745,
        "notes": "Home to University of Arizona. Very affordable. Streetcar near campus. Hot summers.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "gainesville, fl": {
        "city": "Gainesville", "state": "FL", "metro": "Gainesville Metro",
        "rent_1br": 1050, "rent_2br": 1400,
        "groceries": 310, "transport": 35, "utilities": 130,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1775,
        "notes": "Home to University of Florida. No state income tax. Very affordable college town. RTS bus free for UF students.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "portland, or": {
        "city": "Portland", "state": "OR", "metro": "Portland Metro",
        "rent_1br": 1500, "rent_2br": 2000,
        "groceries": 370, "transport": 100, "utilities": 100,
        "phone_internet": 85, "health_insurance": 185,
        "total_monthly_estimate": 2340,
        "notes": "No sales tax. TriMet MAX light rail excellent. No state income tax advantage — OR has income tax.",
        "walkability": "High", "transit_quality": "Excellent",
    },
    "corvallis, or": {
        "city": "Corvallis", "state": "OR", "metro": "Corvallis Metro",
        "rent_1br": 1050, "rent_2br": 1400,
        "groceries": 330, "transport": 35, "utilities": 100,
        "phone_internet": 75, "health_insurance": 180,
        "total_monthly_estimate": 1770,
        "notes": "Home to Oregon State. Affordable, very bike-friendly. Cascades Transit free for OSU students.",
        "walkability": "High", "transit_quality": "Good",
    },
    "st. louis, mo": {
        "city": "St. Louis", "state": "MO", "metro": "St. Louis Metro",
        "rent_1br": 1000, "rent_2br": 1350,
        "groceries": 320, "transport": 70, "utilities": 120,
        "phone_internet": 75, "health_insurance": 175,
        "total_monthly_estimate": 1760,
        "notes": "Home to Washington University in St. Louis. MetroLink light rail covers key areas. Very affordable.",
        "walkability": "Moderate", "transit_quality": "Fair",
    },
    "blacksburg, va": {
        "city": "Blacksburg", "state": "VA", "metro": "New River Valley",
        "rent_1br": 850, "rent_2br": 1100,
        "groceries": 290, "transport": 25, "utilities": 110,
        "phone_internet": 70, "health_insurance": 170,
        "total_monthly_estimate": 1515,
        "notes": "Home to Virginia Tech. Extremely affordable. Blacksburg Transit free for VT students. Rural mountain setting.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
    "charlottesville, va": {
        "city": "Charlottesville", "state": "VA", "metro": "Charlottesville Metro",
        "rent_1br": 1200, "rent_2br": 1600,
        "groceries": 330, "transport": 40, "utilities": 115,
        "phone_internet": 75, "health_insurance": 180,
        "total_monthly_estimate": 1940,
        "notes": "Home to University of Virginia. Affordable college town. CAT/UTS bus free for UVA students.",
        "walkability": "Moderate", "transit_quality": "Good",
    },
}

# Aliases so common name variations resolve correctly
_ALIASES: dict[str, str] = {
    "nyc": "new york, ny",
    "new york city": "new york, ny",
    "nyc, ny": "new york, ny",
    "sf": "san francisco, ca",
    "sf, ca": "san francisco, ca",
    "dc": "washington, dc",
    "washington dc": "washington, dc",
    "wash dc": "washington, dc",
    "la": "los angeles, ca",
    "la, ca": "los angeles, ca",
    "champaign-urbana": "champaign, il",
    "urbana, il": "champaign, il",
    "twin cities": "minneapolis, mn",
    "research triangle": "raleigh, nc",
}

_NATIONAL_AVERAGE = {
    "rent_1br": 1400,
    "rent_2br": 1800,
    "groceries": 350,
    "transport": 80,
    "utilities": 120,
    "phone_internet": 80,
    "health_insurance": 180,
    "total_monthly_estimate": 2210,
    "note": "National averages for reference — actual costs vary significantly by city and neighborhood.",
}


def _normalize_key(city: str, state: str | None) -> str:
    """Build a normalized lookup key from city + optional state."""
    city_clean = city.strip().lower()
    # Remove common suffixes
    city_clean = re.sub(r"\s+(city|metro|area|region)$", "", city_clean)

    if state:
        return f"{city_clean}, {state.strip().lower()}"
    return city_clean


def _lookup(city: str, state: str | None) -> dict[str, Any] | None:
    """Try to find city in dataset, checking aliases and partial matches."""
    key = _normalize_key(city, state)

    # Direct hit
    if key in _CITY_DATA:
        return _CITY_DATA[key]

    # Alias hit
    if key in _ALIASES:
        return _CITY_DATA[_ALIASES[key]]

    # Try without state (when state wasn't provided)
    if state is None:
        city_only = city.strip().lower()
        for data_key, data in _CITY_DATA.items():
            if data_key.startswith(city_only + ",") or data_key == city_only:
                return data
        # Check aliases city-only
        if city_only in _ALIASES:
            return _CITY_DATA[_ALIASES[city_only]]

    return None


# ---------------------------------------------------------------------------
# Tool class
# ---------------------------------------------------------------------------

class CostOfLivingTool:

    async def get_cost_of_living(self, city: str, state: str | None = None) -> dict[str, Any]:
        """
        Get estimated monthly living costs for a US city.

        Returns structured cost breakdown from the hardcoded dataset,
        or national averages with a suggestion to web-search if not found.
        """
        data = _lookup(city, state)

        if data:
            logger.info("cost_of_living: found %s, %s in dataset", data["city"], data.get("state", ""))
            return {
                "found": True,
                "city": data["city"],
                "state": data.get("state"),
                "metro": data.get("metro"),
                "monthly_costs": {
                    "rent_1br": data["rent_1br"],
                    "rent_2br": data["rent_2br"],
                    "groceries": data["groceries"],
                    "transport": data["transport"],
                    "utilities": data["utilities"],
                    "phone_internet": data["phone_internet"],
                    "health_insurance": data["health_insurance"],
                },
                "total_monthly_estimate": data["total_monthly_estimate"],
                "notes": data.get("notes"),
                "walkability": data.get("walkability"),
                "transit_quality": data.get("transit_quality"),
                "source": "Campus Compass estimates (2024-2025 baseline)",
                "disclaimer": "These are estimates for planning purposes. Actual costs vary by neighborhood and lifestyle.",
            }

        # Not found — return national averages + suggestion
        logger.info("cost_of_living: %s not in dataset, returning national averages", city)
        location = f"{city}, {state}" if state else city
        return {
            "found": False,
            "city": city,
            "state": state,
            "suggestion": (
                f"No pre-computed data for {location}. "
                f"Use web_search with query 'cost of living {location} 2025 rent utilities' "
                f"for current estimates."
            ),
            "national_average_reference": _NATIONAL_AVERAGE,
        }


# ---------------------------------------------------------------------------
# Tool definition for Claude
# ---------------------------------------------------------------------------

def get_tool_definition() -> dict[str, Any]:
    city_list = ", ".join(
        f"{v['city']} {v['state']}" for v in _CITY_DATA.values()
    )
    return {
        "name": "get_living_costs",
        "description": (
            "Get estimated monthly living costs for a US city. Returns rent, groceries, "
            "transport, utilities, and other cost estimates relevant to a student budget. "
            "Data is based on 2024-2025 estimates.\n\n"
            f"Covers {len(_CITY_DATA)} major university cities: {city_list}.\n\n"
            "For cities not in the database, returns national averages and suggests using "
            "web_search for current data.\n\n"
            "Note: These are estimates for planning purposes. Actual costs vary by "
            "neighborhood, lifestyle, and housing choices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name. Example: 'Pittsburgh', 'San Francisco', 'Austin'",
                },
                "state": {
                    "type": "string",
                    "description": (
                        "Two-letter state code. Example: 'PA', 'CA', 'TX'. "
                        "Helps disambiguate cities with the same name."
                    ),
                },
            },
            "required": ["city"],
        },
    }


# ---------------------------------------------------------------------------
# Executor — called by the agent's tool dispatcher
# ---------------------------------------------------------------------------

async def execute(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute get_living_costs and return a JSON string for Claude."""
    tool = CostOfLivingTool()
    try:
        result = await tool.get_cost_of_living(
            city=tool_input["city"],
            state=tool_input.get("state"),
        )
    except Exception as exc:
        logger.exception("Unexpected error in cost_of_living execute: %s", exc)
        result = {
            "found": False,
            "error": f"Cost of living tool failed: {exc}",
            "national_average_reference": _NATIONAL_AVERAGE,
        }
    return json.dumps(result, default=str)
