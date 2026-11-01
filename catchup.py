import pandas as pd

def key_moments(innings_df):
    moments = []
    for _, row in innings_df.iterrows():
        if row["wicket_count"] > 0:
            for i, player in enumerate(row["dismissed_players"]):
                kind = row["wicket_types"][i] if i < len(row["wicket_types"]) else "unknown"
                moments.append(f"Over {int(row['over']) + 1}: {player} dismissed ({kind})")
        if row["runs"] == 6:
            moments.append(f"Over {int(row['over']) + 1}: {row['batter']} hit a six")
        elif row["runs"] == 4:
            moments.append(f"Over {int(row['over']) + 1}: {row['batter']} hit a four")
    return moments

def build_catchup(df, innings_num, start_over, end_over):
    innings_df = df[df["innings_num"] == innings_num].copy()
    if innings_df.empty:
        raise ValueError("No deliveries found for this innings.")
    team = innings_df["team"].iloc[0]
    period = innings_df[innings_df["over"].between(start_over, end_over)]
    score_so_far = innings_df[innings_df["over"] <= end_over]
    return {
        "team": team,
        "period_runs": int(period["total_runs"].sum()),
        "period_wickets": int(period["wicket_count"].sum()),
        "fours": int((period["runs"] == 4).sum()),
        "sixes": int((period["runs"] == 6).sum()),
        "total_runs": int(score_so_far["total_runs"].sum()),
        "total_wickets": int(score_so_far["wicket_count"].sum()),
        "moments": key_moments(period),
    }

def make_factual_summary(df, innings_num, start_over, end_over):
    result = build_catchup(df, innings_num, start_over, end_over)
    lines = [
        f"Batting team: {result['team']}",
        f"Innings: {innings_num}",
        f"Selected overs: {start_over + 1} to {end_over + 1}",
        f"Runs in selected period: {result['period_runs']}",
        f"Wickets in selected period: {result['period_wickets']}",
        f"Fours: {result['fours']}; sixes: {result['sixes']}",
        f"Score at end of selected period: {result['team']} "
        f"{result['total_runs']}/{result['total_wickets']}",
        "Key moments:",
    ]
    lines.extend(result["moments"] or ["No fours, sixes, or wickets in this period."])
    return "\n".join(lines)
