import soccerdata as sd 

def fetch_fbref_defense_stats():
    fbref = sd.FBref(leagues="ENG-Premier League", seasons="2324")
    defens_stats= fbref.read_league_stats("Defense")
    print(defens_stats.head())

if __name__ == "__main__":
    fetch_fbref_defense_stats()