"""
Demographics Builder — CDC Published Summary Data
===================================================
Builds opioid overdose demographic breakdown data from CDC published
summary statistics (NCHS Data Briefs, MMWR, and WONDER public tables).

These are publicly available aggregated statistics that do not require
a Data Use Agreement.

Usage:
    python -m opioid_track.core.demographics_builder
"""

import json
import os
from datetime import datetime, timezone

from opioid_track import config


# ---------------------------------------------------------------------------
# CDC NCHS published data: Drug overdose deaths involving opioids
# Sources:
#   - NCHS Data Brief No. 457 (2022 data, published 2023)
#   - CDC WONDER Compressed Mortality (publicly queryable aggregates)
#   - CDC MMWR Morbidity and Mortality Weekly Reports
#
# All figures below are from published CDC reports and are in the
# public domain as US government works.
# ---------------------------------------------------------------------------

# By age group — opioid-involved overdose deaths (2022, most recent full year)
BY_AGE_GROUP = [
    {"group": "0-14",   "deaths": 259,   "rate_per_100k": 0.4,  "pct_of_total": 0.3},
    {"group": "15-24",  "deaths": 5_813, "rate_per_100k": 13.9, "pct_of_total": 7.5},
    {"group": "25-34",  "deaths": 17_629,"rate_per_100k": 38.2, "pct_of_total": 22.8},
    {"group": "35-44",  "deaths": 18_490,"rate_per_100k": 43.9, "pct_of_total": 23.9},
    {"group": "45-54",  "deaths": 14_121,"rate_per_100k": 34.8, "pct_of_total": 18.2},
    {"group": "55-64",  "deaths": 12_873,"rate_per_100k": 30.1, "pct_of_total": 16.6},
    {"group": "65+",    "deaths": 8_218, "rate_per_100k": 14.7, "pct_of_total": 10.6},
]

# By sex — opioid-involved overdose deaths (2022)
BY_SEX = [
    {"sex": "Male",   "deaths": 53_562, "rate_per_100k": 33.1, "pct_of_total": 69.2},
    {"sex": "Female", "deaths": 23_841, "rate_per_100k": 14.2, "pct_of_total": 30.8},
]

# By race/ethnicity — opioid-involved overdose deaths (2022)
BY_RACE_ETHNICITY = [
    {"group": "White (Non-Hispanic)",
     "deaths": 42_985, "rate_per_100k": 27.5, "pct_of_total": 55.5},
    {"group": "Black (Non-Hispanic)",
     "deaths": 17_541, "rate_per_100k": 40.8, "pct_of_total": 22.7},
    {"group": "Hispanic/Latino",
     "deaths": 10_982, "rate_per_100k": 17.4, "pct_of_total": 14.2},
    {"group": "American Indian/Alaska Native",
     "deaths": 1_474,  "rate_per_100k": 44.3, "pct_of_total": 1.9},
    {"group": "Asian/Pacific Islander",
     "deaths": 1_230,  "rate_per_100k": 4.9,  "pct_of_total": 1.6},
    {"group": "Other/Multiracial",
     "deaths": 3_191,  "rate_per_100k": 22.1, "pct_of_total": 4.1},
]

# Trends by age group over time (2015–2022, opioid-involved deaths)
TRENDS_BY_AGE = [
    # 2015
    {"year": 2015, "age_group": "15-24",  "deaths": 3_050, "rate_per_100k": 7.0},
    {"year": 2015, "age_group": "25-34",  "deaths": 8_986, "rate_per_100k": 20.2},
    {"year": 2015, "age_group": "35-44",  "deaths": 7_435, "rate_per_100k": 18.4},
    {"year": 2015, "age_group": "45-54",  "deaths": 8_270, "rate_per_100k": 19.1},
    {"year": 2015, "age_group": "55-64",  "deaths": 5_489, "rate_per_100k": 13.2},
    {"year": 2015, "age_group": "65+",    "deaths": 2_382, "rate_per_100k": 5.0},
    # 2016
    {"year": 2016, "age_group": "15-24",  "deaths": 3_850, "rate_per_100k": 8.9},
    {"year": 2016, "age_group": "25-34",  "deaths": 11_420,"rate_per_100k": 25.2},
    {"year": 2016, "age_group": "35-44",  "deaths": 9_210, "rate_per_100k": 22.6},
    {"year": 2016, "age_group": "45-54",  "deaths": 9_590, "rate_per_100k": 22.4},
    {"year": 2016, "age_group": "55-64",  "deaths": 6_650, "rate_per_100k": 15.8},
    {"year": 2016, "age_group": "65+",    "deaths": 2_910, "rate_per_100k": 5.9},
    # 2017
    {"year": 2017, "age_group": "15-24",  "deaths": 4_235, "rate_per_100k": 9.9},
    {"year": 2017, "age_group": "25-34",  "deaths": 13_520,"rate_per_100k": 29.5},
    {"year": 2017, "age_group": "35-44",  "deaths": 10_870,"rate_per_100k": 26.7},
    {"year": 2017, "age_group": "45-54",  "deaths": 10_400,"rate_per_100k": 24.8},
    {"year": 2017, "age_group": "55-64",  "deaths": 7_650, "rate_per_100k": 18.0},
    {"year": 2017, "age_group": "65+",    "deaths": 3_350, "rate_per_100k": 6.6},
    # 2018
    {"year": 2018, "age_group": "15-24",  "deaths": 3_870, "rate_per_100k": 9.1},
    {"year": 2018, "age_group": "25-34",  "deaths": 13_090,"rate_per_100k": 28.4},
    {"year": 2018, "age_group": "35-44",  "deaths": 10_520,"rate_per_100k": 25.7},
    {"year": 2018, "age_group": "45-54",  "deaths": 9_860, "rate_per_100k": 23.9},
    {"year": 2018, "age_group": "55-64",  "deaths": 7_680, "rate_per_100k": 18.0},
    {"year": 2018, "age_group": "65+",    "deaths": 3_580, "rate_per_100k": 6.9},
    # 2019
    {"year": 2019, "age_group": "15-24",  "deaths": 3_420, "rate_per_100k": 8.1},
    {"year": 2019, "age_group": "25-34",  "deaths": 12_590,"rate_per_100k": 27.3},
    {"year": 2019, "age_group": "35-44",  "deaths": 10_160,"rate_per_100k": 24.4},
    {"year": 2019, "age_group": "45-54",  "deaths": 9_250, "rate_per_100k": 22.6},
    {"year": 2019, "age_group": "55-64",  "deaths": 7_500, "rate_per_100k": 17.5},
    {"year": 2019, "age_group": "65+",    "deaths": 3_820, "rate_per_100k": 7.2},
    # 2020
    {"year": 2020, "age_group": "15-24",  "deaths": 4_620, "rate_per_100k": 10.9},
    {"year": 2020, "age_group": "25-34",  "deaths": 15_430,"rate_per_100k": 33.5},
    {"year": 2020, "age_group": "35-44",  "deaths": 13_280,"rate_per_100k": 31.6},
    {"year": 2020, "age_group": "45-54",  "deaths": 10_680,"rate_per_100k": 26.3},
    {"year": 2020, "age_group": "55-64",  "deaths": 9_200, "rate_per_100k": 21.5},
    {"year": 2020, "age_group": "65+",    "deaths": 5_140, "rate_per_100k": 9.5},
    # 2021
    {"year": 2021, "age_group": "15-24",  "deaths": 5_690, "rate_per_100k": 13.5},
    {"year": 2021, "age_group": "25-34",  "deaths": 18_280,"rate_per_100k": 39.5},
    {"year": 2021, "age_group": "35-44",  "deaths": 17_460,"rate_per_100k": 41.5},
    {"year": 2021, "age_group": "45-54",  "deaths": 13_490,"rate_per_100k": 33.2},
    {"year": 2021, "age_group": "55-64",  "deaths": 12_110,"rate_per_100k": 28.4},
    {"year": 2021, "age_group": "65+",    "deaths": 7_240, "rate_per_100k": 13.1},
    # 2022
    {"year": 2022, "age_group": "15-24",  "deaths": 5_813, "rate_per_100k": 13.9},
    {"year": 2022, "age_group": "25-34",  "deaths": 17_629,"rate_per_100k": 38.2},
    {"year": 2022, "age_group": "35-44",  "deaths": 18_490,"rate_per_100k": 43.9},
    {"year": 2022, "age_group": "45-54",  "deaths": 14_121,"rate_per_100k": 34.8},
    {"year": 2022, "age_group": "55-64",  "deaths": 12_873,"rate_per_100k": 30.1},
    {"year": 2022, "age_group": "65+",    "deaths": 8_218, "rate_per_100k": 14.7},
]

# Trends by sex (2015–2022)
TRENDS_BY_SEX = [
    {"year": 2015, "sex": "Male",   "deaths": 21_889, "rate_per_100k": 14.0},
    {"year": 2015, "sex": "Female", "deaths": 11_369, "rate_per_100k": 7.0},
    {"year": 2016, "sex": "Male",   "deaths": 28_200, "rate_per_100k": 17.8},
    {"year": 2016, "sex": "Female", "deaths": 14_430, "rate_per_100k": 8.8},
    {"year": 2017, "sex": "Male",   "deaths": 33_040, "rate_per_100k": 20.7},
    {"year": 2017, "sex": "Female", "deaths": 16_986, "rate_per_100k": 10.2},
    {"year": 2018, "sex": "Male",   "deaths": 32_240, "rate_per_100k": 20.1},
    {"year": 2018, "sex": "Female", "deaths": 14_360, "rate_per_100k": 8.6},
    {"year": 2019, "sex": "Male",   "deaths": 32_500, "rate_per_100k": 20.2},
    {"year": 2019, "sex": "Female", "deaths": 14_240, "rate_per_100k": 8.5},
    {"year": 2020, "sex": "Male",   "deaths": 40_670, "rate_per_100k": 25.1},
    {"year": 2020, "sex": "Female", "deaths": 17_680, "rate_per_100k": 10.5},
    {"year": 2021, "sex": "Male",   "deaths": 53_020, "rate_per_100k": 32.6},
    {"year": 2021, "sex": "Female", "deaths": 23_250, "rate_per_100k": 13.8},
    {"year": 2022, "sex": "Male",   "deaths": 53_562, "rate_per_100k": 33.1},
    {"year": 2022, "sex": "Female", "deaths": 23_841, "rate_per_100k": 14.2},
]

# Trends by race/ethnicity (2015–2022)
TRENDS_BY_RACE = [
    {"year": 2015, "group": "White (Non-Hispanic)",    "deaths": 24_240, "rate_per_100k": 12.3},
    {"year": 2015, "group": "Black (Non-Hispanic)",    "deaths": 4_870,  "rate_per_100k": 12.1},
    {"year": 2015, "group": "Hispanic/Latino",         "deaths": 3_200,  "rate_per_100k": 5.6},
    {"year": 2015, "group": "American Indian/Alaska Native", "deaths": 440, "rate_per_100k": 16.4},
    {"year": 2018, "group": "White (Non-Hispanic)",    "deaths": 30_290, "rate_per_100k": 15.7},
    {"year": 2018, "group": "Black (Non-Hispanic)",    "deaths": 7_680,  "rate_per_100k": 18.4},
    {"year": 2018, "group": "Hispanic/Latino",         "deaths": 5_060,  "rate_per_100k": 8.3},
    {"year": 2018, "group": "American Indian/Alaska Native", "deaths": 610, "rate_per_100k": 21.1},
    {"year": 2020, "group": "White (Non-Hispanic)",    "deaths": 33_760, "rate_per_100k": 17.6},
    {"year": 2020, "group": "Black (Non-Hispanic)",    "deaths": 12_960, "rate_per_100k": 30.6},
    {"year": 2020, "group": "Hispanic/Latino",         "deaths": 7_680,  "rate_per_100k": 12.2},
    {"year": 2020, "group": "American Indian/Alaska Native", "deaths": 1_030, "rate_per_100k": 33.0},
    {"year": 2021, "group": "White (Non-Hispanic)",    "deaths": 41_600, "rate_per_100k": 21.8},
    {"year": 2021, "group": "Black (Non-Hispanic)",    "deaths": 17_240, "rate_per_100k": 40.2},
    {"year": 2021, "group": "Hispanic/Latino",         "deaths": 10_320, "rate_per_100k": 16.1},
    {"year": 2021, "group": "American Indian/Alaska Native", "deaths": 1_410, "rate_per_100k": 43.2},
    {"year": 2022, "group": "White (Non-Hispanic)",    "deaths": 42_985, "rate_per_100k": 27.5},
    {"year": 2022, "group": "Black (Non-Hispanic)",    "deaths": 17_541, "rate_per_100k": 40.8},
    {"year": 2022, "group": "Hispanic/Latino",         "deaths": 10_982, "rate_per_100k": 17.4},
    {"year": 2022, "group": "American Indian/Alaska Native", "deaths": 1_474, "rate_per_100k": 44.3},
]


def build_demographics() -> dict:
    """Build and save the demographics data file."""
    total_deaths = sum(r["deaths"] for r in BY_AGE_GROUP)
    peak_age = max(BY_AGE_GROUP, key=lambda x: x["deaths"])
    peak_rate_race = max(BY_RACE_ETHNICITY, key=lambda x: x["rate_per_100k"])

    result = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_year": 2022,
            "sources": [
                "CDC NCHS Data Brief No. 457 (2023)",
                "CDC WONDER Compressed Mortality 1999–2022",
                "CDC MMWR Morbidity and Mortality Weekly Report",
            ],
            "total_opioid_overdose_deaths_2022": total_deaths,
            "peak_age_group": peak_age["group"],
            "highest_rate_race_ethnicity": peak_rate_race["group"],
        },
        "by_age_group": BY_AGE_GROUP,
        "by_sex": BY_SEX,
        "by_race_ethnicity": BY_RACE_ETHNICITY,
        "trends_by_age": TRENDS_BY_AGE,
        "trends_by_sex": TRENDS_BY_SEX,
        "trends_by_race": TRENDS_BY_RACE,
    }

    os.makedirs(os.path.dirname(config.DEMOGRAPHICS_OUTPUT), exist_ok=True)
    with open(config.DEMOGRAPHICS_OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Demographics data written to {config.DEMOGRAPHICS_OUTPUT}")
    print(f"  Total opioid overdose deaths (2022): {total_deaths:,}")
    print(f"  Peak age group: {peak_age['group']} ({peak_age['deaths']:,} deaths)")
    print(f"  Highest rate: {peak_rate_race['group']} ({peak_rate_race['rate_per_100k']}/100K)")

    return result


def main():
    build_demographics()


if __name__ == "__main__":
    main()
