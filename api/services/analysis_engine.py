def analyze_match(match_data: dict) -> dict:
    adv_score = match_data.get("form_advantage", 0)
    if adv_score > 3:
        match_comment = "Ev sahibi takım net favori."
    elif adv_score < -3:
        match_comment = "Deplasman takımı daha formda."
    else:
        match_comment = "İki takım denk güçte, riskli maç."
    return {
            "game_id": match_data["game_id"],
            "home_club_id": match_data["home_club_id"],
            "away_club_id": match_data["away_club_id"],
            "form_advantage_score": adv_score,
            "analysis": match_comment
        }

def calculate_form_score(form_advantage: float) -> dict:
    if form_advantage >= 5:
        score = 80
        reason = "Home is so strong"
    elif form_advantage >= 2:
        score = 65
        reason = "Home is a bit powerfull"
    elif form_advantage <= -5:
        score = 20
        reason = "Away is so strong"
    elif form_advantage <= -2:
        score = 35
        reason = "Away is a bit powerful"
    else:
        score = 50
        reason = "Both teams are equal"
        
    return {
        "score": score,
        "reason": reason
    }