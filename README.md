# FanIQ -- Cricket Match Catch-up & Stats Assistant

FanIQ helps cricket fans catch up on a match quickly and ask cricket
questions in one place. It uses ball-by-ball match data for match
summaries and charts, with an AI-powered assistant for broader cricket
stats.

## Features

-   **Match catch-up:** Select a match, innings and over range to get a
    short summary.
-   **Key moments:** Highlights wickets, boundaries and important events
    from the selected overs.
-   **Score insights:** Displays runs, wickets, fours and sixes, with
    score-progression and runs-per-over charts.
-   **Ask FanIQ:** Ask cricket questions and view answers with source
    links.
-   **Match data:** Replays matches from Cricsheet JSON files stored
    locally.

## Tech Stack

Python · Streamlit · Pandas · Plotly · Groq · Cricsheet JSON

## Project Structure

``` text
Match_Catchup_Assistant/
├── app.py                 # Streamlit interface
├── catchup.py             # Match catch-up summaries
├── charts.py              # Score and over charts
├── data_processing.py     # Cricsheet data loading and processing
├── groq_summary.py        # AI-generated match summaries
├── stats_agent.py         # Cricket Q&A agent
├── web_search_tool.py     # Web search for cricket questions
├── ipl_json/              # Match JSON files
├── requirements.txt
├── README.md
└── .env                   # API key (create locally)
```

## Run Locally

1.  Clone the repository and open the project folder.

2.  Create and activate a virtual environment:

    ``` bash
    python -m venv .venv
    ```

    Windows:

    ``` bash
    .venv\\Scripts\\activate
    ```

3.  Install dependencies:

    ``` bash
    pip install -r requirements.txt
    ```

4.  Create a `.env` file in the project root and add your Groq API key:

    ``` env
    GROQ_API_KEY=your_api_key_here
    ```

5.  Add Cricsheet match JSON files to the `ipl_json/` folder, then start
    the app:

    ``` bash
    streamlit run app.py
    ```

## Note

The match catch-up feature uses the local Cricsheet ball-by-ball dataset
and is not connected to a live match feed. AI-generated answers and
summaries may occasionally be inaccurate; check the linked sources for
current stats.
