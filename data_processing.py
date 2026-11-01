import json
from pathlib import Path
import pandas as pd


def list_match_files(data_dir):
    """Return all JSON match files in the given directory."""
    data_dir = Path(data_dir)
    return sorted(data_dir.glob("*.json"))


def load_match(match_path):
    """Load a Cricsheet JSON file."""
    match_path = Path(match_path)

    with open(match_path, "r", encoding="utf-8") as file:
        return json.load(file)


def parse_match(match):
    """Convert one loaded match JSON into ball-by-ball rows."""

    # If a file path is passed, load the JSON first
    if isinstance(match, (str, Path)):
        match = load_match(match)

    rows = []

    for innings_num, innings in enumerate(
        match.get("innings", []), start=1
    ):
        team = innings.get("team", "Unknown")

        for over_data in innings.get("overs", []):
            over_num = over_data.get("over", 0)

            for ball_num, delivery in enumerate(
                over_data.get("deliveries", []), start=1
            ):
                runs = delivery.get("runs", {})
                wickets = delivery.get("wickets", [])

                rows.append({
                    "innings_num": innings_num,
                    "team": team,
                    "over": over_num,
                    "ball": ball_num,
                    "batter": delivery.get("batter", ""),
                    "bowler": delivery.get("bowler", ""),
                    "runs": runs.get("batter", 0),
                    "total_runs": runs.get("total", 0),
                    "extras": delivery.get("extras", {}),
                    "wickets": wickets,
                    "wicket_count": len(wickets),
                    "wicket_types": [
                        wicket.get("kind", "unknown")
                        for wicket in wickets
                    ],
                    "dismissed_players": [
                        wicket.get("player_out", "unknown")
                        for wicket in wickets
                    ],
                })

    return pd.DataFrame(rows)


def load_all_matches(data_dir):
    """Load and combine all match JSON files."""
    all_matches = []

    json_files = list_match_files(data_dir)

    if not json_files:
        print(f"No JSON files found in: {data_dir}")
        return pd.DataFrame()

    for match_path in json_files:
        try:
            match_data = load_match(match_path)
            match_df = parse_match(match_data)

            if not match_df.empty:
                all_matches.append(match_df)

        except Exception as error:
            print(f"Skipping {match_path.name}: {error}")

    if all_matches:
        return pd.concat(all_matches, ignore_index=True)

    return pd.DataFrame()


# Example usage / testing
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "ipl_json"

ball_by_ball_df = load_all_matches(DATA_DIR)

print("Dataset shape:", ball_by_ball_df.shape)
print(ball_by_ball_df.head())