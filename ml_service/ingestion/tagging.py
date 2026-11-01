"""
Rule-based season / occasion inference from accords.

The seed CSV (and many Fragrantica pages) lack explicit season/occasion data, so
we derive coarse tags from the main accords. These tags feed the embedding text
and the payload, improving "winter date night" style queries.
"""

SEASON_MAP = {
    "fresh": "spring summer", "citrus": "spring summer", "aquatic": "summer",
    "woody": "autumn winter", "amber": "autumn winter", "vanilla": "winter",
    "floral": "spring", "rose": "spring", "spicy": "winter autumn",
    "gourmand": "winter", "musky": "all seasons", "musk": "all seasons",
    "leather": "autumn winter", "powdery": "spring autumn", "fruity": "spring summer",
    "green": "spring", "earthy": "autumn", "sweet": "winter",
}

OCCASION_MAP = {
    "fresh": "office daytime", "citrus": "office casual", "floral": "romantic daytime",
    "vanilla": "evening date", "amber": "evening", "spicy": "evening date",
    "gourmand": "evening casual", "woody": "casual", "leather": "evening formal",
    "aquatic": "sporty casual", "musky": "everyday", "musk": "everyday",
    "powdery": "daytime", "sweet": "evening date", "fruity": "casual daytime",
}


def _collect(accords, mapping) -> str:
    tags: set[str] = set()
    for accord in accords or []:
        a = str(accord).lower().strip()
        for key, val in mapping.items():
            if key in a:
                tags.update(val.split())
    return " ".join(sorted(tags))


def infer_season(accords) -> str:
    return _collect(accords, SEASON_MAP)


def infer_occasion(accords) -> str:
    return _collect(accords, OCCASION_MAP)
