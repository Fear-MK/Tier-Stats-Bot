# "bAD W olf" -> "badwolf"
def format_name(name: str):
    return ''.join(name.split()).lower()

RT_TIER_MAP = {
    't1': "Tier 1",
    't2': "Tier 2",
    't3': "Tier 3",
    't4': "Tier 4",
    't5': "Tier 5",
    't6': "Tier 6",
    't7': "Tier 7",
    'top50': "Top 50",
    '50': "Top 50",
    '1': "Tier 1",
    '2': "Tier 2",
    '3': "Tier 3",
    '4': "Tier 4",
    '5': "Tier 5",
    '6': "Tier 6",
    '7': "Tier 7",
    'tier1': "Tier 1",
    'tier2': "Tier 2",
    'tier3': "Tier 3",
    'tier4': "Tier 4",
    'tier5': "Tier 4",
    'tier6': "Tier 6",
    'tier7': "Tier 7",
    'tier50': "Top 50",
    'tiertop50': "Top 50"
}

CT_TIER_MAP = {
    't1': "Tier 1",
    't2': "Tier 2",
    't3': "Tier 3",
    't4': "Tier 4",
    't5': "Tier 5",
    't6': "Tier 6",
    'top50': "Top 50",
    '50': "Top 50",
    '1': "Tier 1",
    '2': "Tier 2",
    '3': "Tier 3",
    '4': "Tier 4",
    '5': "Tier 5",
    '6': "Tier 6",
    'tier1': "Tier 1",
    'tier2': "Tier 2",
    'tier3': "Tier 3",
    'tier4': "Tier 4",
    'tier5': "Tier 4",
    'tier6': "Tier 6",
    'tier50': "Top 50",
    'tiertop50': "Top 50"
}

EVENT_FORMAT_MAP = {
    "1": "FFA",
    "2": "2v2",
    "3": "3v3",
    "4": "4v4",
    "6": "6v6",
    "ffa": "FFA",
    "2v2": "2v2",
    "3v3": "3v3",
    "4v4": "4v4",
    "6v6": "6v6",
}
