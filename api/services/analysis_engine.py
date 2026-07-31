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
        reason = "Home team has a clear form advantage."
    elif form_advantage >= 2:
        score = 65
        reason = "Home team is slightly ahead in form."
    elif form_advantage <= -5:
        score = 20
        reason = "Away team has a massive form advantage."
    elif form_advantage <= -2:
        score = 35
        reason = "Away team is slightly ahead in form."
    else:
        score = 50
        reason = "The teams have equal form."
        
    return {
        "score": score,
        "reason": reason
    }

def calculate_goals_score(btts_tendency: float, over_2_5_tendency: float) -> dict:
    avg_tendency = (btts_tendency + over_2_5_tendency) / 2
    
    if avg_tendency >= 0.75:
        score = 85
        reason = "Statistics indicate a high-scoring match."
    elif avg_tendency >= 0.60:
        score = 70
        reason = "Above average goal potential."
    elif avg_tendency <= 0.25:
        score = 15
        reason = "Statistics point to a low-scoring defensive match."
    elif avg_tendency <= 0.40:
        score = 30
        reason = "Below average goal potential."
    else:
        score = 50
        reason = "Unclear goal potential, unpredictable match."
        
    return {
        "score": score,
        "reason": reason
    }

def analyze_match(match_data: dict) -> dict:
    form_adv = match_data.get("form_advantage", 0.0)
    btts_tend = match_data.get("btts_tendency", 0.0)
    over_25_tend = match_data.get("over_2_5_tendency", 0.0)

    form_result = calculate_form_score(form_adv)
    goals_result = calculate_goals_score(btts_tend, over_25_tend)

    return {
        "game_id": match_data.get("game_id"),
        "home_club_id": match_data.get("home_club_id"),
        "away_club_id": match_data.get("away_club_id"),
        "home_strength_score": form_result["score"],
        "goal_expectation_score": goals_result["score"],
        "reasons": [
            form_result["reason"],
            goals_result["reason"]
        ]
    }