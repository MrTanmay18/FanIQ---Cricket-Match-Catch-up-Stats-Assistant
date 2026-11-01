import pandas as pd

def prepare_chart_data(df, innings_num):
    innings_df = (
        df[df["innings_num"] == innings_num]
        .copy()
        .sort_values(["over", "ball"])
        .reset_index(drop=True)
    )
    if innings_df.empty:
        return innings_df, pd.DataFrame()

    innings_df["delivery_number"] = range(1, len(innings_df) + 1)
    innings_df["cumulative_runs"] = innings_df["total_runs"].cumsum()
    innings_df["cumulative_wickets"] = innings_df["wicket_count"].cumsum()
    innings_df["delivery_label"] = (
        (innings_df["over"] + 1).astype(str)
        + "."
        + innings_df.groupby("over").cumcount().add(1).astype(str)
    )

    over_data = (
        innings_df.groupby("over")
        .agg(over_runs=("total_runs", "sum"), over_wickets=("wicket_count", "sum"))
        .reset_index()
    )
    over_data["cumulative_runs"] = over_data["over_runs"].cumsum()
    over_data["cumulative_wickets"] = over_data["over_wickets"].cumsum()
    over_data["over_label"] = over_data["over"].apply(lambda x: f"Over {x + 1}")
    return innings_df, over_data
