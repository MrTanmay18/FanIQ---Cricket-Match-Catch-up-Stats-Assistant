import json
import os
import re
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

from data_processing import list_match_files, load_match, parse_match
from catchup import build_catchup, make_factual_summary
from charts import prepare_chart_data
from groq_summary import generate_ai_catchup
from stats_agent import answer_stats_question


# =========================================================
# PAGE CONFIG
# =========================================================
load_dotenv()

st.set_page_config(
    page_title="FanIQ | Cricket Assistant",
    page_icon="🏏",
    layout="wide",
)

# Design tokens (kept in one place so the CSS and Plotly stay in sync)
INK = "#12141A"        # text + hero tile
CANVAS = "#F3F4F6"     # page background
TILE = "#FFFFFF"       # bento tile surface
LINE = "#E5E7EB"       # tile borders
MUTED = "#6B7280"      # secondary text
ACCENT = "#E4202C"     # the single accent colour


# =========================================================
# STYLES — Bento grid + minimalism
# Requires Streamlit >= 1.39 (st.container(key=...))
# =========================================================
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Manrope:wght@400;500;600&display=swap');

:root {{
    --ink: {INK};
    --canvas: {CANVAS};
    --tile: {TILE};
    --line: {LINE};
    --muted: {MUTED};
    --accent: {ACCENT};
}}

/* ---------- Page ---------- */
html, body, [data-testid="stApp"] {{
    background: var(--canvas);
    color: var(--ink);
    font-family: 'Manrope', system-ui, sans-serif;
}}
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
    display: none;
}}
.block-container {{
    max-width: 1180px;
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}}
[data-testid="stVerticalBlock"] {{ gap: 0.9rem; }}
[data-testid="stHorizontalBlock"] {{ gap: 0.9rem; }}

h1, h2, h3, h4 {{
    font-family: 'Bricolage Grotesque', 'Manrope', sans-serif;
    letter-spacing: -0.02em;
    color: var(--ink);
}}

/* ---------- Wordmark ---------- */
.wordmark {{
    display: flex;
    align-items: baseline;
    gap: 0.9rem;
    margin-bottom: 0.4rem;
}}
.wordmark b {{
    font-family: 'Bricolage Grotesque', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: -0.04em;
}}
.wordmark b i {{ color: var(--accent); font-style: normal; }}
.wordmark span {{ color: var(--muted); font-size: 0.98rem; }}

/* ---------- Tabs ---------- */
[data-baseweb="tab-list"] {{ gap: 0.4rem; border-bottom: none; }}
button[role="tab"] {{
    border-radius: 999px;
    padding: 0.45rem 1.1rem;
    height: auto;
    background: transparent;
    font-weight: 600;
    color: var(--muted);
}}
button[role="tab"][aria-selected="true"] {{
    background: var(--ink);
    color: #fff;
}}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display: none; }}

/* ---------- Bento tiles ---------- */
[class*="st-key-tile"] {{
    background: var(--tile);
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 1.3rem 1.45rem;
}}
[class*="st-key-tile_metric"] {{
    border-radius: 16px;
    padding: 1rem 1.2rem;
}}
.st-key-tile_hero {{
    background: var(--ink);
    border-color: var(--ink);
    color: #fff;
    border-radius: 28px;
    min-height: 250px;
}}

.tile-title {{
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 600;
    font-size: 1.05rem;
    margin: 0 0 0.2rem 0;
}}
.tile-sub {{ color: var(--muted); font-size: 0.88rem; margin-bottom: 0.6rem; }}

/* Hero */
.hero-team {{ font-size: 0.95rem; color: rgba(255,255,255,.7); }}
.hero-score {{
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 700;
    font-size: 5.2rem;
    line-height: 1;
    letter-spacing: -0.05em;
    margin: 0.5rem 0 0.7rem 0;
}}
.hero-score span {{ color: var(--accent); font-size: 3rem; letter-spacing: -0.03em; }}
.hero-note {{ font-size: 0.92rem; color: rgba(255,255,255,.75); line-height: 1.5; }}

/* Metric tiles */
.metric-value {{
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 700;
    font-size: 2.3rem;
    line-height: 1.1;
    letter-spacing: -0.03em;
}}
.metric-label {{ color: var(--muted); font-size: 0.85rem; }}

/* Moments */
.moments {{ max-height: 360px; overflow-y: auto; padding-right: 0.3rem; }}
.moment {{
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--line);
    font-size: 0.92rem;
    line-height: 1.45;
}}
.moment:last-child {{ border-bottom: none; }}

/* Match meta */
.match-meta {{ margin-top: 0.4rem; line-height: 1.7; font-size: 0.93rem; }}
.match-meta strong {{ font-size: 1.08rem; }}
.match-meta span {{ color: var(--muted); display: block; }}

/* ---------- Inputs ---------- */
[data-baseweb="select"] > div,
[data-baseweb="input"],
[data-baseweb="base-input"] {{
    border-radius: 12px !important;
    background: #FAFAFB !important;
    border-color: var(--line) !important;
}}
label, [data-testid="stWidgetLabel"] p {{
    font-size: 0.86rem !important;
    color: var(--muted) !important;
    font-weight: 500;
}}

/* Buttons */
.stButton > button, .stFormSubmitButton > button {{
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--tile);
    color: var(--ink);
    font-weight: 600;
    padding: 0.5rem 1.2rem;
    transition: border-color .15s, background .15s;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{
    border-color: var(--ink);
    color: var(--ink);
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
.stFormSubmitButton > button[kind="primaryFormSubmit"] {{
    background: var(--ink);
    border-color: var(--ink);
    color: #fff;
    width: 100%;
}}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {{
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
}}
.stButton > button:focus-visible {{
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}}

/* Suggestion chips on the Ask tab */
[class*="st-key-chip"] .stButton > button {{
    width: 100%;
    text-align: left;
    border-radius: 16px;
    padding: 0.9rem 1rem;
    min-height: 4.2rem;
    font-weight: 500;
    line-height: 1.35;
}}

/* Sources under answers */
.sources {{
    margin-top: 1.1rem;
    padding-top: 0.9rem;
    border-top: 1px solid var(--line);
}}
.sources-label {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 0.3rem; }}
a.source {{
    display: block;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--line);
    text-decoration: none;
    color: var(--ink) !important;
}}
a.source:last-child {{ border-bottom: none; }}
a.source .source-title {{ display: block; font-size: 0.93rem; font-weight: 600; }}
a.source .source-url {{
    display: block;
    font-size: 0.8rem;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
a.source .source-snippet {{ display: block; font-size: 0.85rem; color: var(--muted); margin-top: 0.15rem; }}
a.source:hover .source-title {{ text-decoration: underline; }}
a.source:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}

.footnote {{ color: var(--muted); font-size: 0.8rem; margin-top: 1.4rem; }}

@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================
@st.cache_data
def get_match_details(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        match = json.load(file)

    info = match.get("info", {})
    teams = info.get("teams", [])

    team1 = teams[0] if len(teams) > 0 else "Team 1"
    team2 = teams[1] if len(teams) > 1 else "Team 2"

    dates = info.get("dates", [])
    match_date = str(dates[0]) if dates else "Date unavailable"
    venue = info.get("venue", "Venue unavailable")

    return {
        "label": f"{team1} vs {team2} | {match_date} | {venue}",
        "teams": f"{team1} vs {team2}",
        "date": match_date,
        "venue": venue,
    }


@st.cache_data(show_spinner=False)
def get_match_df(file_path):
    """Parse a match once instead of on every Streamlit rerun."""
    return parse_match(load_match(Path(file_path)))


def style_figure(fig, height=420):
    """Minimal Plotly theme that matches the tiles."""
    fig.update_layout(
        height=height,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Manrope, sans-serif", color=INK),
        legend_title_text="",
        legend=dict(orientation="h", y=1.1, x=0),
        title=None,
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, zeroline=False)
    fig.update_yaxes(gridcolor="#EEF0F3", zeroline=False)
    return fig


def metric_tile(key, value, label):
    with st.container(key=f"tile_metric_{key}"):
        st.markdown(
            f'<div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div>',
            unsafe_allow_html=True,
        )


def search_web(question):
    """
    Answer a cricket question with Tavily web search.
    Returns {"answer": str, "sources": [{"title", "url", "snippet"}]}.
    Needs TAVILY_API_KEY in your .env file and `pip install tavily-python`.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is missing from your .env file")

    from tavily import TavilyClient

    query = (
        question
        if re.search(r"cricket|ipl", question, re.IGNORECASE)
        else f"{question} cricket"
    )

    response = TavilyClient(api_key=api_key).search(
        query=query,
        search_depth="advanced",
        max_results=6,
        include_answer=True,
    )

    sources, seen = [], set()
    for item in response.get("results", []):
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append(
            {
                "title": item.get("title") or urlparse(url).netloc,
                "url": url,
                "snippet": (item.get("content") or "").strip(),
            }
        )

    return {"answer": (response.get("answer") or "").strip(), "sources": sources}


def render_sources(sources, show_snippets=False):
    """Draw the reference links under an answer."""
    if not sources:
        return
    rows = ""
    for src in sources:
        snippet = ""
        if show_snippets and src["snippet"]:
            snippet = (
                f'<span class="source-snippet">'
                f'{escape(src["snippet"][:240])}...</span>'
            )
        rows += (
            f'<a class="source" href="{escape(src["url"], quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'<span class="source-title">{escape(src["title"])}</span>'
            f'<span class="source-url">{escape(src["url"])}</span>'
            f"{snippet}</a>"
        )
    st.markdown(
        f'<div class="sources"><div class="sources-label">Sources</div>'
        f"{rows}</div>",
        unsafe_allow_html=True,
    )


def render_web_answer(result):
    """Answer text first, then the references."""
    if result["answer"]:
        st.write(result["answer"])
        render_sources(result["sources"])
    elif result["sources"]:
        st.write(
            "I couldn't find one direct answer, but these sources "
            "cover your question."
        )
        render_sources(result["sources"], show_snippets=True)
    else:
        st.write("No results found. Try rephrasing your question.")


PRESETS = {
    "Last 3 overs": 3,
    "Last 5 overs": 5,
    "Last 10 overs": 10,
    "Choose overs": None,
}


# =========================================================
# HEADER
# =========================================================
st.markdown(
    '<div class="wordmark"><b>Fan<i>IQ</i></b>'
    "<span>Just joined the match? Catch up in under a minute.</span></div>",
    unsafe_allow_html=True,
)

tab_catchup, tab_agent = st.tabs(["Catch up", "Ask FanIQ"])


# =========================================================
# TAB 1: MATCH CATCH-UP
# =========================================================
with tab_catchup:

    DATA_DIR = Path(__file__).parent / "ipl_json"
    match_files = list_match_files(DATA_DIR)

    if not match_files:
        with st.container(key="tile_empty"):
            st.markdown(
                '<div class="tile-title">No match data found</div>'
                f'<div class="tile-sub">Looked in {escape(str(DATA_DIR))}. '
                "Extract the Cricsheet IPL JSON ZIP into the project's "
                "ipl_json folder, then refresh.</div>",
                unsafe_allow_html=True,
            )

    else:
        match_details = {
            str(path): get_match_details(str(path)) for path in match_files
        }
        match_files = sorted(
            match_files,
            key=lambda path: match_details[str(path)]["date"],
            reverse=True,
        )

        # ---------------- Row 1: pick match | pick what you missed -------
        col_match, col_missed = st.columns([5, 7])

        with col_match:
            with st.container(key="tile_match"):
                st.markdown(
                    '<div class="tile-title">Match</div>', unsafe_allow_html=True
                )
                selected_path = st.selectbox(
                    "Search by team, date or venue",
                    options=[str(path) for path in match_files],
                    format_func=lambda path: match_details[path]["label"],
                    key="catchup_match_select",
                )
                selected_match = match_details[selected_path]
                st.markdown(
                    f'<div class="match-meta"><strong>'
                    f'{escape(selected_match["teams"])}</strong>'
                    f'<span>{escape(selected_match["date"])}</span>'
                    f'<span>{escape(selected_match["venue"])}</span></div>',
                    unsafe_allow_html=True,
                )

        df = get_match_df(selected_path)

        with col_missed:
            with st.container(key="tile_missed"):
                st.markdown(
                    '<div class="tile-title">What did you miss?</div>',
                    unsafe_allow_html=True,
                )

                if df.empty:
                    st.error("No delivery data found for this match.")
                    st.stop()

                innings_options = sorted(df["innings_num"].unique())

                selected_innings = st.selectbox(
                    "Innings",
                    innings_options,
                    index=len(innings_options) - 1,  # latest innings first
                    format_func=lambda inning: (
                        f"Innings {inning}: "
                        f"{df[df['innings_num'] == inning]['team'].iloc[0]}"
                    ),
                    key="catchup_innings_select",
                )

                innings_df = df[df["innings_num"] == selected_innings]
                min_over = int(innings_df["over"].min())
                max_over = int(innings_df["over"].max())

                preset = st.radio(
                    "Range",
                    list(PRESETS.keys()),
                    index=1,
                    horizontal=True,
                    key="catchup_preset",
                )

                if PRESETS[preset] is not None:
                    end_idx = max_over
                    start_idx = max(min_over, max_over - PRESETS[preset] + 1)
                else:
                    c1, c2 = st.columns(2)
                    start_over = c1.number_input(
                        "From over",
                        min_value=min_over + 1,
                        max_value=max_over + 1,
                        value=max(min_over, max_over - 4) + 1,
                        step=1,
                        key="catchup_start_over",
                    )
                    end_over_input = c2.number_input(
                        "To over",
                        min_value=min_over + 1,
                        max_value=max_over + 1,
                        value=max_over + 1,
                        step=1,
                        key="catchup_end_over",
                    )
                    # Cricsheet over indexes are zero-based
                    start_idx = int(start_over) - 1
                    end_idx = int(end_over_input) - 1

                start_over = start_idx + 1
                end_over = end_idx + 1

                invalid_range = start_idx > end_idx
                if invalid_range:
                    st.warning("The first over must come before the last over.")

                current_selection = (
                    str(selected_path),
                    int(selected_innings),
                    start_idx,
                    end_idx,
                )

                st.session_state.setdefault("show_results", False)
                st.session_state.setdefault(
                    "previous_selection", current_selection
                )
                st.session_state.setdefault("ai_cache", {})

                if st.session_state.previous_selection != current_selection:
                    st.session_state.show_results = False
                    st.session_state.previous_selection = current_selection

                if st.button(
                    "Catch me up",
                    type="primary",
                    key="generate_catchup_button",
                    disabled=invalid_range,
                ):
                    st.session_state.show_results = True

        # ---------------- Results -----------------------------------------
        if st.session_state.show_results and not invalid_range:

            facts = make_factual_summary(
                df, int(selected_innings), start_idx, end_idx
            )
            result = build_catchup(
                df, int(selected_innings), start_idx, end_idx
            )

            # ---- Row 2: hero score | AI summary
            col_hero, col_ai = st.columns([5, 7])

            with col_hero:
                with st.container(key="tile_hero"):
                    st.markdown(
                        f'<div class="hero-team">{escape(str(result["team"]))}'
                        f"</div>"
                        f'<div class="hero-score">{result["total_runs"]}'
                        f'<span>/{result["total_wickets"]}</span></div>'
                        f'<div class="hero-note">Score after over {end_over}<br>'
                        f'{result["period_runs"]} runs and '
                        f'{result["period_wickets"]} wickets in overs '
                        f"{start_over} to {end_over}</div>",
                        unsafe_allow_html=True,
                    )

            with col_ai:
                with st.container(key="tile_ai"):
                    st.markdown(
                        '<div class="tile-title">The story so far</div>'
                        '<div class="tile-sub">Written from the ball-by-ball '
                        "data for the overs you chose.</div>",
                        unsafe_allow_html=True,
                    )

                    cache = st.session_state.ai_cache
                    if current_selection in cache:
                        st.write(cache[current_selection])
                    else:
                        with st.spinner("Writing your catch-up..."):
                            try:
                                ai_summary = generate_ai_catchup(facts)
                                cache[current_selection] = ai_summary
                                st.write(ai_summary)
                            except Exception as exc:
                                st.warning(f"AI summary unavailable: {exc}")
                                st.write(facts)

            # ---- Row 3: four metric tiles
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                metric_tile("runs", result["period_runs"], "Runs scored")
            with m2:
                metric_tile("wkts", result["period_wickets"], "Wickets")
            with m3:
                metric_tile("fours", result["fours"], "Fours")
            with m4:
                metric_tile("sixes", result["sixes"], "Sixes")

            # ---- Chart data
            ball_data, over_data = prepare_chart_data(
                df, int(selected_innings)
            )
            selected_balls = ball_data[
                ball_data["over"].between(start_idx, end_idx)
            ].copy()
            selected_overs = over_data[
                over_data["over"].between(start_idx, end_idx)
            ].copy()

            # ---- Row 4: score chart | key moments
            col_chart, col_moments = st.columns([8, 4])

            with col_chart:
                with st.container(key="tile_chart"):
                    st.markdown(
                        '<div class="tile-title">Score progression</div>',
                        unsafe_allow_html=True,
                    )
                    chart_view = st.radio(
                        "View",
                        ["Over by over", "Ball by ball"],
                        horizontal=True,
                        key="score_chart_view",
                    )

                    if chart_view == "Over by over":
                        fig = px.line(
                            selected_overs,
                            x="over_label",
                            y="cumulative_runs",
                            markers=True,
                            labels={
                                "over_label": "Over",
                                "cumulative_runs": "Innings score",
                                "over_runs": "Runs in over",
                                "over_wickets": "Wickets in over",
                            },
                            hover_data=["over_runs", "over_wickets"],
                            color_discrete_sequence=[ACCENT],
                        )
                        fig.update_traces(
                            line=dict(width=3), marker=dict(size=7)
                        )
                    else:
                        fig = px.line(
                            selected_balls,
                            x="delivery_number",
                            y="cumulative_runs",
                            markers=True,
                            labels={
                                "delivery_number": "Delivery",
                                "cumulative_runs": "Innings score",
                                "delivery_label": "Over.Ball",
                                "batter": "Batter",
                                "bowler": "Bowler",
                                "total_runs": "Runs from delivery",
                            },
                            hover_data=[
                                "delivery_label",
                                "batter",
                                "bowler",
                                "total_runs",
                            ],
                            color_discrete_sequence=[ACCENT],
                        )
                        fig.update_traces(
                            line=dict(width=2), marker=dict(size=4)
                        )

                        wicket_data = selected_balls[
                            selected_balls["wicket_count"] > 0
                        ]
                        if not wicket_data.empty:
                            fig.add_trace(
                                go.Scatter(
                                    x=wicket_data["delivery_number"],
                                    y=wicket_data["cumulative_runs"],
                                    mode="markers",
                                    name="Wicket",
                                    marker=dict(
                                        size=12,
                                        symbol="x",
                                        color=INK,
                                        line=dict(width=2, color=INK),
                                    ),
                                    text=wicket_data[
                                        "dismissed_players"
                                    ].apply(lambda players: ", ".join(players)),
                                    hovertemplate=(
                                        "Delivery: %{x}<br>"
                                        "Score: %{y}<br>"
                                        "Out: %{text}<extra></extra>"
                                    ),
                                )
                            )

                    fig.update_layout(
                        xaxis_title="Over"
                        if chart_view == "Over by over"
                        else "Delivery",
                        yaxis_title="Innings score",
                    )
                    style_figure(fig, height=400)
                    st.plotly_chart(fig, use_container_width=True)

            with col_moments:
                with st.container(key="tile_moments"):
                    st.markdown(
                        '<div class="tile-title">Key moments</div>',
                        unsafe_allow_html=True,
                    )
                    if result["moments"]:
                        items = "".join(
                            f'<div class="moment">{escape(str(m))}</div>'
                            for m in result["moments"]
                        )
                        st.markdown(
                            f'<div class="moments">{items}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="tile-sub">No fours, sixes or wickets '
                            "in these overs.</div>",
                            unsafe_allow_html=True,
                        )

            # ---- Row 5: runs per over
            with st.container(key="tile_runs_per_over"):
                st.markdown(
                    '<div class="tile-title">Runs in each over</div>',
                    unsafe_allow_html=True,
                )
                fig_runs = px.bar(
                    selected_overs,
                    x="over_label",
                    y="over_runs",
                    labels={"over_label": "Over", "over_runs": "Runs in over"},
                    text="over_runs",
                    color_discrete_sequence=[INK],
                )
                fig_runs.update_traces(textposition="outside", marker_cornerradius=6)
                fig_runs.update_layout(
                    xaxis_title="Over", yaxis_title="Runs", hovermode="closest"
                )
                style_figure(fig_runs, height=300)
                fig_runs.update_layout(hovermode="closest")
                st.plotly_chart(fig_runs, use_container_width=True)


# =========================================================
# TAB 2: ASK FANIQ
# =========================================================
with tab_agent:

    EXAMPLES = [
        "Who are the top 10 IPL run scorers?",
        "Which team has won the most IPL titles?",
        "Who scored the fastest century in IPL?",
        "Top IPL run scorer?",
    ]

    st.session_state.setdefault("active_question", "")
    st.session_state.setdefault("answers", {})

    with st.container(key="tile_ask"):
        st.markdown(
            '<div class="tile-title">Ask anything about cricket</div>'
            '<div class="tile-sub">FanIQ checks the local IPL dataset and '
            "searches the web for wider cricket questions.</div>",
            unsafe_allow_html=True,
        )
        with st.form("stats_agent_form", border=False):
            user_question = st.text_input(
                "Your question",
                placeholder="Who are the top 10 IPL run scorers?",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Ask FanIQ", type="primary")

        if submitted and user_question.strip():
            st.session_state.active_question = user_question.strip()

    # Suggested questions as small bento tiles
    chip_cols = st.columns(len(EXAMPLES))
    for i, (col, example) in enumerate(zip(chip_cols, EXAMPLES)):
        with col:
            with st.container(key=f"chip_{i}"):
                if st.button(example, key=f"chip_btn_{i}"):
                    st.session_state.active_question = example

    question = st.session_state.active_question
    if question:
        with st.container(key="tile_answer"):
            st.markdown(
                f'<div class="tile-title">{escape(question)}</div>',
                unsafe_allow_html=True,
            )

            # Cached so other reruns don't search again
            result = st.session_state.answers.get(question)

            if result is None:
                with st.spinner("Searching the web..."):
                    try:
                        result = search_web(question)
                    except Exception as exc:
                        st.warning(
                            f"Web search unavailable ({exc}). "
                            "Using the local dataset instead."
                        )
                        result = None

                if result is None:
                    try:
                        full_answer = st.write_stream(
                            answer_stats_question(question)
                        )
                        result = {"answer": full_answer, "sources": []}
                        st.session_state.answers[question] = result
                    except Exception as exc:
                        st.error(f"Unable to answer this question: {exc}")
                else:
                    st.session_state.answers[question] = result
                    render_web_answer(result)
            else:
                render_web_answer(result)

# =========================================================
# FOOTER
# =========================================================
st.markdown(
    '<div class="footnote">Match replays use Cricsheet ball-by-ball data. '
    "This prototype is not connected to a live match feed.</div>",
    unsafe_allow_html=True,
)