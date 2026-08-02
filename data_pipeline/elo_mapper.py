# Understat İsimleri -> ClubElo İsimleri
UNDERSTAT_TO_CLUBELO = {
    # İngiltere (Premier League) Sorunlu İsimler
    "Manchester City": "ManCity",
    "Manchester United": "ManUnited",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Forest",
    "Wolverhampton Wanderers": "Wolves",
    "Sheffield United": "SheffieldUnited",
    
    # İleride Top 5 ligin tamamını çektiğimizde lazım olacak diğer liglerden bazıları
    "Bayern Munich": "Bayern",
    "Bayer Leverkusen": "Leverkusen",
    "Borussia Dortmund": "Dortmund",
    "Eintracht Frankfurt": "Frankfurt",
    "Paris Saint Germain": "PSG",
    "Real Madrid": "RealMadrid",
    "Atletico Madrid": "Atletico",
    "Athletic Club": "Athletic",
    "Inter": "Inter",
    "AC Milan": "Milan",
    "Juventus": "Juventus"
}

def get_clubelo_name(understat_name):
    # Eğer sözlükte karşılığı varsa onu dön, yoksa ismin kendisini (boşluksuz haliyle) dönmeyi dene
    if understat_name in UNDERSTAT_TO_CLUBELO:
        return UNDERSTAT_TO_CLUBELO[understat_name]
    
    # Standart bir kural olarak boşlukları silmek çoğu takımda işe yarar (Örn: Aston Villa -> AstonVilla)
    return understat_name.replace(" ", "")
