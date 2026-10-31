import re
from fractions import Fraction

MINUTE_PATTERN = re.compile(r"(\d+)'(?:\+(\d+)')?")
GOAL_TYPES = ("goal", "penalty_goal", "own_goal")
BET365_PROVIDER = "Bet 365"
BET365_FIELDS = {
    "preMatchFullTimeResultHome": "b365_home",
    "preMatchFullTimeResultDraw": "b365_draw",
    "preMatchFullTimeResultAway": "b365_away",
    "preMatchGoalLineOver": "b365_over",
    "preMatchGoalLineUnder": "b365_under",
    "preMatchDoubleChanceHomeOrDraw": "b365_dc_home_draw",
    "preMatchDoubleChanceHomeOrAway": "b365_dc_home_away",
    "preMatchDoubleChanceDrawOrAway": "b365_dc_draw_away",
}


def parse_minute(display_value: str):
    match = MINUTE_PATTERN.search(display_value or "")
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2) or 0)


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value):
    try:
        return float(str(value).replace("%", ""))
    except (TypeError, ValueError):
        return None


def fractional_to_decimal(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.upper() in ("EVS", "EVENS"):
        return 2.0
    try:
        return round(float(Fraction(text)) + 1, 4)
    except (ValueError, ZeroDivisionError):
        return None


def detail_type(detail: dict):
    if detail.get("scoringPlay") and not detail.get("shootout"):
        if detail.get("ownGoal"):
            return "own_goal"
        if detail.get("penaltyKick"):
            return "penalty_goal"
        return "goal"
    if detail.get("redCard"):
        return "red_card"
    if detail.get("yellowCard"):
        return "yellow_card"
    return None


def parse_scoreboard_event(event: dict, league: str):
    competition = event["competitions"][0]
    sides = {c["homeAway"]: c for c in competition["competitors"]}
    home, away = sides["home"], sides["away"]
    status = event["status"]["type"]

    events = []
    for detail in competition.get("details") or []:
        kind = detail_type(detail)
        if kind is None:
            continue
        minute, added = parse_minute(detail.get("clock", {}).get("displayValue"))
        events.append({
            "event_id": event["id"],
            "team_id": detail.get("team", {}).get("id"),
            "type": kind,
            "minute": minute,
            "added_time": added,
            "half": None if minute is None else (1 if minute <= 45 else 2),
        })

    match = {
        "event_id": event["id"],
        "league": league,
        "season": event.get("season", {}).get("year"),
        "kickoff_utc": event["date"],
        "status": status.get("name"),
        "state": status.get("state"),
        "completed": bool(status.get("completed")),
        "home_team_id": home["id"],
        "home_team": home["team"]["displayName"],
        "away_team_id": away["id"],
        "away_team": away["team"]["displayName"],
        "home_goals": to_int(home.get("score")) if status.get("completed") else None,
        "away_goals": to_int(away.get("score")) if status.get("completed") else None,
        "venue": competition.get("venue", {}).get("fullName"),
        "attendance": competition.get("attendance"),
    }
    return match, events


def parse_team_stats(summary: dict, event_id: str):
    competitors = (summary.get("header", {}).get("competitions") or [{}])[0].get("competitors", [])
    home_away = {c["id"]: c.get("homeAway") for c in competitors}
    rows = []
    for team in (summary.get("boxscore") or {}).get("teams") or []:
        stats = team.get("statistics") or []
        if not stats:
            continue
        row = {"event_id": event_id, "team_id": team["team"]["id"], "home_away": home_away.get(team["team"]["id"])}
        for stat in stats:
            row[stat["name"]] = to_float(stat.get("displayValue"))
        rows.append(row)
    return rows


def parse_bet365_odds(summary: dict, event_id: str):
    for provider in summary.get("odds") or []:
        if provider.get("provider", {}).get("name") != BET365_PROVIDER:
            continue
        team_odds = (provider.get("bettingOdds") or {}).get("teamOdds") or {}
        if not any(key.startswith("preMatch") for key in team_odds):
            continue
        row = {"event_id": event_id}
        for source, target in BET365_FIELDS.items():
            row[target] = fractional_to_decimal((team_odds.get(source) or {}).get("value"))
        row["b365_goal_line"] = to_float((team_odds.get("preMatchOverUnderHandicap") or {}).get("value"))
        return row
    return None


def parse_referee(summary: dict):
    for official in (summary.get("gameInfo") or {}).get("officials") or []:
        position = (official.get("position") or {}).get("name", "")
        if not position or "referee" in position.lower() and "assistant" not in position.lower():
            return official.get("displayName") or official.get("fullName")
    return None
