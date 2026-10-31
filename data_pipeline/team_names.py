UNDERSTAT_TO_CLUBELO = {
    "Manchester City": "ManCity",
    "Manchester United": "ManUnited",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Forest",
    "Wolverhampton Wanderers": "Wolves",
    "Sheffield United": "SheffieldUnited",
    "Bayern Munich": "Bayern",
    "Bayer Leverkusen": "Leverkusen",
    "Borussia Dortmund": "Dortmund",
    "Eintracht Frankfurt": "Frankfurt",
    "Paris Saint Germain": "PSG",
    "Real Madrid": "RealMadrid",
    "Atletico Madrid": "Atletico",
    "Athletic Club": "Athletic",
    "AC Milan": "Milan",
}


def to_clubelo(understat_name: str) -> str:
    return UNDERSTAT_TO_CLUBELO.get(understat_name, understat_name.replace(" ", ""))
