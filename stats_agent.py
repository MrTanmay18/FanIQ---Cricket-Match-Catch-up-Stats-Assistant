# stats_agent.py

import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from data_processing import list_match_files, parse_match
from web_search_tool import web_search_tool

load_dotenv()

DATA_DIR = Path(__file__).parent / "ipl_json"
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


# ============================================================
# LOAD LOCAL IPL DATA
# ============================================================

@st.cache_data(show_spinner=False)
def load_all_ipl_data():
    """Load parsed ball-by-ball data from all local IPL JSON files."""

    match_files = list_match_files(DATA_DIR)
    all_frames = []

    for match_file in match_files:
        try:
            match_df = parse_match(match_file)

            if isinstance(match_df, pd.DataFrame) and not match_df.empty:
                match_df = match_df.copy()
                match_df["source_match"] = Path(match_file).name
                all_frames.append(match_df)

        except Exception as error:
            print(f"Skipping {match_file}: {error}")

    if not all_frames:
        return pd.DataFrame()

    return pd.concat(all_frames, ignore_index=True)


# ============================================================
# COLUMN HELPERS
# ============================================================

def find_column(df, possible_names):
    """Find a column using possible column names."""

    normalized_columns = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in df.columns
    }

    for name in possible_names:
        normalized_name = name.strip().lower().replace(" ", "_")

        if normalized_name in normalized_columns:
            return normalized_columns[normalized_name]

    return None


def get_batter_column(df):
    return find_column(
        df,
        ["batter", "batsman", "striker", "player"]
    )


def get_bowler_column(df):
    return find_column(df, ["bowler"])


def get_runs_column(df):
    return find_column(
        df,
        ["batter_runs", "runs_batter", "batter runs", "runs"]
    )


def get_wickets_column(df):
    return find_column(
        df,
        ["bowler_wickets", "wicket_count", "wickets", "bowler wickets"]
    )


# ============================================================
# LOCAL IPL STATISTICS TOOLS
# ============================================================

def top_run_scorers(df, top_n=10):
    batter_col = get_batter_column(df)
    runs_col = get_runs_column(df)

    if batter_col is None or runs_col is None:
        return (
            "Could not find batter and runs columns in the parsed data.\n"
            f"Available columns: {list(df.columns)}"
        )

    data = df[[batter_col, runs_col]].copy()
    data[runs_col] = pd.to_numeric(
        data[runs_col], errors="coerce"
    ).fillna(0)

    result = (
        data.groupby(batter_col)[runs_col]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )

    result.columns = ["Player", "Runs"]
    result.index = result.index + 1

    return (
        f"Top {top_n} IPL run scorers from the local dataset:\n"
        f"{result.to_string()}"
    )


def top_wicket_takers(df, top_n=10):
    bowler_col = get_bowler_column(df)
    wickets_col = get_wickets_column(df)

    if bowler_col is None or wickets_col is None:
        return (
            "Could not find bowler and wicket columns in the parsed data.\n"
            f"Available columns: {list(df.columns)}"
        )

    data = df[[bowler_col, wickets_col]].copy()
    data[wickets_col] = pd.to_numeric(
        data[wickets_col], errors="coerce"
    ).fillna(0)

    result = (
        data.groupby(bowler_col)[wickets_col]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )

    result.columns = ["Player", "Wickets"]
    result.index = result.index + 1

    return (
        f"Top {top_n} IPL wicket takers from the local dataset:\n"
        f"{result.to_string()}"
    )


def player_runs(df, player_name):
    batter_col = get_batter_column(df)
    runs_col = get_runs_column(df)

    if batter_col is None or runs_col is None:
        return "Player run statistics are unavailable in the parsed dataset."

    data = df.copy()
    data[runs_col] = pd.to_numeric(
        data[runs_col], errors="coerce"
    ).fillna(0)

    player_data = data[
        data[batter_col].astype(str).str.contains(
            re.escape(player_name),
            case=False,
            na=False
        )
    ]

    if player_data.empty:
        return f"No IPL records found for {player_name}."

    total_runs = int(player_data[runs_col].sum())
    player_names = player_data[batter_col].dropna().unique().tolist()

    return (
        f"Player: {', '.join(map(str, player_names))}\n"
        f"Runs in the loaded IPL dataset: {total_runs}"
    )


# ============================================================
# QUESTION ROUTING
# ============================================================

def is_cricket_question(question):
    cricket_keywords = [
        "cricket", "ipl", "t20", "odi", "test",
        "batter", "batsman", "bowler", "wicket",
        "runs", "six", "four", "match", "innings",
        "world cup", "player", "team", "score",
        "strike rate", "economy", "century",
        "half century", "captain"
    ]

    question = question.lower()

    return any(keyword in question for keyword in cricket_keywords)


def choose_tool(question):
    question_lower = question.lower()

    web_keywords = [
        "latest", "today", "current", "recent",
        "live", "news", "ranking", "ranked",
        "worldwide", "all-time", "international",
        "world cup", "this season"
    ]

    if any(keyword in question_lower for keyword in web_keywords):
        return "web_search"

    if any(keyword in question_lower for keyword in [
        "top scorer", "top run", "most runs", "highest run"
    ]):
        return "top_run_scorers"

    if any(keyword in question_lower for keyword in [
        "top bowler", "most wickets", "wicket taker",
        "highest wickets"
    ]):
        return "top_wicket_takers"

    if "runs" in question_lower or "scored" in question_lower:
        return "player_runs"

    # Use web search for other cricket questions.
    return "web_search"


def run_local_tool(question, tool_name):
    df = load_all_ipl_data()

    if df.empty:
        return (
            "No IPL data was loaded. Check that JSON files are present "
            "in the ipl_json folder and parse_match() works."
        )

    if tool_name == "top_run_scorers":
        match = re.search(r"top\s*(\d+)", question.lower())
        top_n = int(match.group(1)) if match else 10
        top_n = max(1, min(top_n, 20))

        return top_run_scorers(df, top_n)

    if tool_name == "top_wicket_takers":
        match = re.search(r"top\s*(\d+)", question.lower())
        top_n = int(match.group(1)) if match else 10
        top_n = max(1, min(top_n, 20))

        return top_wicket_takers(df, top_n)

    if tool_name == "player_runs":
        patterns = [
            r"how many runs did ([a-z .'-]+)",
            r"runs scored by ([a-z .'-]+)",
            r"([a-z .'-]+) runs"
        ]

        player_name = None

        for pattern in patterns:
            match = re.search(pattern, question.lower())

            if match:
                player_name = match.group(1).strip(" ?.")
                break

        if not player_name:
            return (
                "Please specify a player name. Example: "
                "'How many IPL runs did Virat Kohli score?'"
            )

        return player_runs(df, player_name)

    return "The requested local statistics tool is not supported."


# ============================================================
# GROQ STREAMING RESPONSE
# ============================================================

def stream_groq_answer(question, tool_result, source_type):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        yield "GROQ_API_KEY is missing from your .env file."
        return

    client = Groq(api_key=api_key)

    system_prompt = f"""
You are FanIQ, a concise cricket statistics and catch-up assistant.

Source type: {source_type}

Answer using ONLY the supplied tool result.
Do not invent scores, statistics, dates, rankings, player facts, or outcomes.

Rules:
- Keep answers concise, usually 2-5 sentences.
- Preserve values and ranking order from the tool result.
- If the result does not contain the answer, say it could not be verified.
- For local data, state that it comes from the loaded IPL dataset.
- For web results, state that the information was found online.
- Include source URLs from web results when available.
- Do not claim information is live unless the source confirms it.
"""

    response_stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Tool result:\n{tool_result}"
                )
            }
        ],
        temperature=0.2,
        max_tokens=500,
        stream=True
    )

    for chunk in response_stream:
        if chunk.choices:
            content = chunk.choices[0].delta.content

            if content:
                yield content


# ============================================================
# MAIN AGENT FUNCTION
# ============================================================

def answer_stats_question(question):
    question = question.strip()

    if not question:
        yield "Please enter a cricket question."
        return

    if not is_cricket_question(question):
        yield (
            "I can answer cricket-related questions about players, teams, "
            "matches, statistics, and cricket news."
        )
        return

    tool_name = choose_tool(question)

    try:
        if tool_name == "web_search":
            tool_result = web_search_tool(
                question,
                max_results=5
            )
            source_type = "Internet search"

        else:
            tool_result = run_local_tool(
                question,
                tool_name
            )
            source_type = "Local Cricsheet IPL dataset"

    except Exception as error:
        yield f"Unable to retrieve information: {error}"
        return

    yield from stream_groq_answer(
        question=question,
        tool_result=tool_result,
        source_type=source_type
    )
