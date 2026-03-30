import re
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import Pitch
from mplsoccer import PyPizza
import config


# =========================================================
# BASIC DATA PREP
# =========================================================

def load_and_clean_data(file_obj):
    if file_obj is None:
        raise ValueError("No file provided.")

    if hasattr(file_obj, "name"):
        file_name = file_obj.name.lower()
    else:
        file_name = str(file_obj).lower()

    if file_name.endswith(".csv"):
        df = pd.read_csv(file_obj)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        df = pd.read_excel(file_obj)
    else:
        raise ValueError("Unsupported file format. Please upload CSV or Excel.")

    df.columns = [str(col).strip().lower() for col in df.columns]

    if config.COL_TEAM in df.columns:
        df[config.COL_TEAM] = df[config.COL_TEAM].ffill().bfill()

    if config.COL_PLAYER in df.columns:
        df[config.COL_PLAYER] = df[config.COL_PLAYER].astype(str).str.strip()

    if config.COL_EVENT_TYPE in df.columns:
        df[config.COL_EVENT_TYPE] = df[config.COL_EVENT_TYPE].astype(str).str.strip()

    if config.COL_LABELS in df.columns:
        df[config.COL_LABELS] = df[config.COL_LABELS].fillna("").astype(str)

    return df


def validate_columns(df):
    required_cols = [
        config.COL_TEAM,
        config.COL_PLAYER,
        config.COL_EVENT_TYPE,
        config.COL_X,
        config.COL_Y,
        config.COL_END_X,
        config.COL_END_Y,
        config.COL_BEGIN,
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    return missing_cols


def _safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def _labels_text(row):
    return str(row.get(config.COL_LABELS, "")).strip().lower()


def _event_text(row):
    return str(row.get(config.COL_EVENT_TYPE, "")).strip().lower()


def _is_pass(row):
    return _event_text(row) == "pass"


def _is_shot(row):
    return _event_text(row) == "shot"


def _is_complete_pass(row):
    return _is_pass(row) and "complete" in _labels_text(row)


def _prepare_event_df(df):
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    for col in [config.COL_X, config.COL_Y, config.COL_END_X, config.COL_END_Y, config.COL_BEGIN]:
        if col in work.columns:
            work[col] = _safe_numeric(work[col])

    if config.COL_END in work.columns:
        work[config.COL_END] = _safe_numeric(work[config.COL_END])

    work = work.sort_values(config.COL_BEGIN, kind="stable").reset_index(drop=True)
    return work


def _player_display_name(player_name):
    if pd.isna(player_name):
        return ""

    player_name = str(player_name).strip()
    match = re.search(r"(\d+)$", player_name)
    if match:
        return match.group(1)

    parts = player_name.split()
    if len(parts) == 1:
        return parts[0][:10]

    return parts[-1][:10]


def _single_player_only(df):
    if df is None or df.empty or config.COL_PLAYER not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work = work[~work[config.COL_PLAYER].astype(str).str.contains(",", na=False)].copy()
    work[config.COL_PLAYER] = work[config.COL_PLAYER].astype(str).str.strip()
    work = work[work[config.COL_PLAYER] != ""].copy()
    return work


def calculate_metrics(df):
    if df is None or df.empty:
        return 0, 0, 0

    total_events = len(df)

    if config.COL_EVENT_TYPE not in df.columns:
        return total_events, 0, 0

    event_series = df[config.COL_EVENT_TYPE].astype(str).str.lower().str.strip()
    total_passes = int((event_series == "pass").sum())
    total_shots = int((event_series == "shot").sum())

    return total_events, total_passes, total_shots


# =========================================================
# BASIC VISUALS
# =========================================================

def create_pass_map(df):
    if df is None or df.empty:
        return None

    needed_cols = [
        config.COL_EVENT_TYPE,
        config.COL_X,
        config.COL_Y,
        config.COL_END_X,
        config.COL_END_Y,
    ]
    for col in needed_cols:
        if col not in df.columns:
            return None

    work = _prepare_event_df(df)
    passes = work[work[config.COL_EVENT_TYPE].astype(str).str.lower().str.strip() == "pass"].copy()
    passes = passes.dropna(subset=[config.COL_X, config.COL_Y, config.COL_END_X, config.COL_END_Y])

    if passes.empty:
        return None

    pitch = Pitch(
        pitch_type="custom",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#1e1e1e",
        line_color="white"
    )
    fig, ax = pitch.draw(figsize=(10, 7))

    pitch.arrows(
        passes[config.COL_X],
        passes[config.COL_Y],
        passes[config.COL_END_X],
        passes[config.COL_END_Y],
        ax=ax,
        color="cyan",
        width=1.5,
        headwidth=4,
        headlength=4,
        alpha=0.75
    )

    pitch.scatter(
        passes[config.COL_X],
        passes[config.COL_Y],
        ax=ax,
        color="red",
        s=18,
        alpha=0.85
    )

    ax.set_title("Pass Map", color="white", fontsize=14)
    fig.patch.set_facecolor("#1e1e1e")
    return fig


def create_heatmap(df):
    if df is None or df.empty:
        return None

    needed_cols = [config.COL_X, config.COL_Y]
    for col in needed_cols:
        if col not in df.columns:
            return None

    work = _prepare_event_df(df)
    work = work.dropna(subset=[config.COL_X, config.COL_Y])

    if work.empty:
        return None

    pitch = Pitch(
        pitch_type="custom",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#1e1e1e",
        line_color="white"
    )
    fig, ax = pitch.draw(figsize=(10, 7))

    sns.kdeplot(
        data=work,
        x=config.COL_X,
        y=config.COL_Y,
        fill=True,
        cmap="YlOrRd",
        alpha=0.65,
        thresh=0.05,
        levels=50,
        ax=ax
    )

    ax.set_title("Heatmap", color="white", fontsize=14)
    fig.patch.set_facecolor("#1e1e1e")
    return fig


def create_shot_map(df):
    if df is None or df.empty:
        return None

    needed_cols = [config.COL_EVENT_TYPE, config.COL_X, config.COL_Y]
    for col in needed_cols:
        if col not in df.columns:
            return None

    work = _prepare_event_df(df)
    shots = work[work[config.COL_EVENT_TYPE].astype(str).str.lower().str.strip() == "shot"].copy()
    shots = shots.dropna(subset=[config.COL_X, config.COL_Y])

    if shots.empty:
        return None

    pitch = Pitch(
        pitch_type="custom",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#1e1e1e",
        line_color="white"
    )
    fig, ax = pitch.draw(figsize=(10, 7))

    pitch.scatter(
        shots[config.COL_X],
        shots[config.COL_Y],
        ax=ax,
        color="yellow",
        edgecolors="black",
        s=90,
        alpha=0.9
    )

    ax.set_title("Shot Map", color="white", fontsize=14)
    fig.patch.set_facecolor("#1e1e1e")
    return fig


# =========================================================
# PASS NETWORK
# =========================================================

def _infer_pass_receivers(df, max_distance=10):
    needed_cols = [
        config.COL_PLAYER,
        config.COL_TEAM,
        config.COL_EVENT_TYPE,
        config.COL_LABELS,
        config.COL_X,
        config.COL_Y,
        config.COL_END_X,
        config.COL_END_Y,
    ]
    for col in needed_cols:
        if col not in df.columns:
            return pd.DataFrame(columns=["passer", "receiver", "x", "y", "end_x", "end_y"])

    work = _prepare_event_df(df)
    inferred_rows = []

    for i in range(len(work) - 1):
        current_row = work.iloc[i]
        next_row = work.iloc[i + 1]

        if not _is_complete_pass(current_row):
            continue

        passer = str(current_row.get(config.COL_PLAYER, "")).strip()
        receiver = str(next_row.get(config.COL_PLAYER, "")).strip()

        if passer == "" or receiver == "":
            continue

        team_now = str(current_row.get(config.COL_TEAM, "")).strip().lower()
        team_next = str(next_row.get(config.COL_TEAM, "")).strip().lower()

        if team_now != team_next:
            continue

        if passer == receiver:
            continue

        end_x = current_row.get(config.COL_END_X)
        end_y = current_row.get(config.COL_END_Y)
        next_x = next_row.get(config.COL_X)
        next_y = next_row.get(config.COL_Y)

        if pd.isna(end_x) or pd.isna(end_y) or pd.isna(next_x) or pd.isna(next_y):
            continue

        distance = np.sqrt((end_x - next_x) ** 2 + (end_y - next_y) ** 2)

        if distance <= max_distance:
            inferred_rows.append({
                "passer": passer,
                "receiver": receiver,
                "x": current_row.get(config.COL_X),
                "y": current_row.get(config.COL_Y),
                "end_x": end_x,
                "end_y": end_y,
            })

    return pd.DataFrame(inferred_rows)


def create_pass_network(df, min_pass_count=2, max_distance=10):
    if df is None or df.empty:
        return None, None

    needed_cols = [
        config.COL_PLAYER,
        config.COL_TEAM,
        config.COL_EVENT_TYPE,
        config.COL_X,
        config.COL_Y,
        config.COL_END_X,
        config.COL_END_Y,
    ]
    for col in needed_cols:
        if col not in df.columns:
            return None, None

    work = _prepare_event_df(df)
    work = work.dropna(subset=[config.COL_PLAYER, config.COL_X, config.COL_Y])

    if work.empty:
        return None, None

    inferred = _infer_pass_receivers(work, max_distance=max_distance)
    if inferred.empty:
        return None, None

    edge_df = (
        inferred.groupby(["passer", "receiver"])
        .size()
        .reset_index(name="pass_count")
        .sort_values("pass_count", ascending=False)
    )

    edge_df = edge_df[edge_df["pass_count"] >= min_pass_count].copy()

    if edge_df.empty:
        return None, inferred

    involved_players = set(edge_df["passer"]).union(set(edge_df["receiver"]))

    player_pos = (
        work[work[config.COL_PLAYER].isin(involved_players)]
        .groupby(config.COL_PLAYER)[[config.COL_X, config.COL_Y]]
        .mean()
        .reset_index()
        .rename(columns={
            config.COL_PLAYER: "player",
            config.COL_X: "avg_x",
            config.COL_Y: "avg_y"
        })
    )

    sent_counts = edge_df.groupby("passer")["pass_count"].sum().reset_index(name="sent")
    recv_counts = edge_df.groupby("receiver")["pass_count"].sum().reset_index(name="received")

    player_stats = player_pos.merge(
        sent_counts, left_on="player", right_on="passer", how="left"
    ).merge(
        recv_counts, left_on="player", right_on="receiver", how="left"
    )

    player_stats["sent"] = player_stats["sent"].fillna(0)
    player_stats["received"] = player_stats["received"].fillna(0)
    player_stats["involvement"] = player_stats["sent"] + player_stats["received"]

    edge_plot = edge_df.merge(
        player_pos.rename(columns={"player": "passer", "avg_x": "x1", "avg_y": "y1"}),
        on="passer",
        how="left"
    ).merge(
        player_pos.rename(columns={"player": "receiver", "avg_x": "x2", "avg_y": "y2"}),
        on="receiver",
        how="left"
    )

    edge_plot = edge_plot.dropna(subset=["x1", "y1", "x2", "y2"])

    if edge_plot.empty or player_stats.empty:
        return None, inferred

    max_edge = edge_plot["pass_count"].max()
    max_node = max(player_stats["involvement"].max(), 1)

    pitch = Pitch(
        pitch_type="custom",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#1e1e1e",
        line_color="white"
    )

    fig, ax = pitch.draw(figsize=(12, 8))
    fig.patch.set_facecolor("#1e1e1e")

    for _, row in edge_plot.iterrows():
        lw = 1.5 + (row["pass_count"] / max_edge) * 7
        alpha = 0.25 + (row["pass_count"] / max_edge) * 0.55

        pitch.lines(
            row["x1"], row["y1"],
            row["x2"], row["y2"],
            lw=lw,
            color="#00d9ff",
            alpha=alpha,
            zorder=1,
            ax=ax
        )

    node_sizes = 500 + (player_stats["involvement"] / max_node) * 1800

    pitch.scatter(
        player_stats["avg_x"],
        player_stats["avg_y"],
        s=node_sizes,
        color="#ffcc00",
        edgecolors="black",
        linewidth=1.5,
        alpha=0.95,
        ax=ax,
        zorder=3
    )

    for _, row in player_stats.iterrows():
        ax.text(
            row["avg_x"],
            row["avg_y"],
            _player_display_name(row["player"]),
            color="black",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            zorder=4
        )

    ax.set_title("Pass Network", color="white", fontsize=16)
    return fig, edge_df


# =========================================================
# ADVANCED PASSING
# =========================================================

def _distance_to_goal(x, y, goal_x=105, goal_y=34):
    return np.sqrt((goal_x - x) ** 2 + (goal_y - y) ** 2)


def _get_pass_subset(df):
    if df is None or df.empty:
        return pd.DataFrame()

    needed_cols = [
        config.COL_PLAYER,
        config.COL_EVENT_TYPE,
        config.COL_X,
        config.COL_Y,
        config.COL_END_X,
        config.COL_END_Y,
    ]
    for col in needed_cols:
        if col not in df.columns:
            return pd.DataFrame()

    work = _prepare_event_df(df)
    passes = work[work.apply(_is_pass, axis=1)].copy()
    passes = passes.dropna(subset=[config.COL_X, config.COL_Y, config.COL_END_X, config.COL_END_Y])

    if config.COL_LABELS not in passes.columns:
        passes[config.COL_LABELS] = ""

    return passes


def get_progressive_passes(df, min_gain=9):
    passes = _get_pass_subset(df)
    if passes.empty:
        return passes

    start_dist = _distance_to_goal(passes[config.COL_X], passes[config.COL_Y])
    end_dist = _distance_to_goal(passes[config.COL_END_X], passes[config.COL_END_Y])

    passes["goal_distance_reduction"] = start_dist - end_dist
    passes["is_progressive"] = passes["goal_distance_reduction"] >= min_gain

    return passes[passes["is_progressive"]].copy()


def get_key_passes(df):
    passes = _get_pass_subset(df)
    if passes.empty:
        return passes

    work = _prepare_event_df(df).copy()
    key_indexes = set()

    for i in range(len(work) - 1):
        row = work.iloc[i]
        nxt = work.iloc[i + 1]

        if not _is_pass(row):
            continue

        labels = _labels_text(row)
        if "key" in labels:
            key_indexes.add(i)
            continue

        same_team = str(row.get(config.COL_TEAM, "")).strip().lower() == str(nxt.get(config.COL_TEAM, "")).strip().lower()
        next_is_shot = _is_shot(nxt)

        if same_team and next_is_shot:
            key_indexes.add(i)

    if not key_indexes:
        labeled = passes[passes[config.COL_LABELS].astype(str).str.lower().str.contains("key", na=False)].copy()
        return labeled

    key_df = work.iloc[sorted(list(key_indexes))].copy()
    key_df = key_df[key_df.apply(_is_pass, axis=1)].copy()
    key_df = key_df.dropna(subset=[config.COL_X, config.COL_Y, config.COL_END_X, config.COL_END_Y])

    return key_df


def get_final_third_entries(df, final_third_x=70):
    passes = _get_pass_subset(df)
    if passes.empty:
        return passes

    entries = passes[
        (passes[config.COL_X] < final_third_x) &
        (passes[config.COL_END_X] >= final_third_x)
    ].copy()

    return entries


def _draw_pass_subset(passes_df, title, line_color, start_color, end_color):
    if passes_df is None or passes_df.empty:
        return None

    pitch = Pitch(
        pitch_type="custom",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#1e1e1e",
        line_color="white"
    )

    fig, ax = pitch.draw(figsize=(10, 7))
    fig.patch.set_facecolor("#1e1e1e")

    pitch.arrows(
        passes_df[config.COL_X],
        passes_df[config.COL_Y],
        passes_df[config.COL_END_X],
        passes_df[config.COL_END_Y],
        ax=ax,
        color=line_color,
        width=2,
        headwidth=4,
        headlength=5,
        alpha=0.85
    )

    pitch.scatter(
        passes_df[config.COL_X],
        passes_df[config.COL_Y],
        ax=ax,
        color=start_color,
        edgecolors="black",
        s=45,
        alpha=0.95,
        zorder=3
    )

    pitch.scatter(
        passes_df[config.COL_END_X],
        passes_df[config.COL_END_Y],
        ax=ax,
        color=end_color,
        edgecolors="black",
        s=40,
        alpha=0.95,
        zorder=3
    )

    ax.set_title(title, color="white", fontsize=15)
    return fig


def create_progressive_passes_map(df):
    progressive = get_progressive_passes(df)
    fig = _draw_pass_subset(
        progressive,
        title="Progressive Passes",
        line_color="#00d9ff",
        start_color="#ffcc00",
        end_color="#00ff88"
    )
    return fig, progressive


def create_key_passes_map(df):
    key_passes = get_key_passes(df)
    fig = _draw_pass_subset(
        key_passes,
        title="Key Passes",
        line_color="#ff4d4d",
        start_color="#ffd166",
        end_color="#ffffff"
    )
    return fig, key_passes


def create_final_third_entries_map(df):
    final_third = get_final_third_entries(df)
    fig = _draw_pass_subset(
        final_third,
        title="Final Third Entries",
        line_color="#a66cff",
        start_color="#ffcc00",
        end_color="#00d9ff"
    )
    return fig, final_third


def create_advanced_passing_summary(df):
    prog = get_progressive_passes(df)
    keyp = get_key_passes(df)
    third = get_final_third_entries(df)

    def _count_by_player(dataframe, col_name):
        if dataframe is None or dataframe.empty:
            return pd.DataFrame(columns=[config.COL_PLAYER, col_name])

        return dataframe.groupby(config.COL_PLAYER).size().reset_index(name=col_name)

    prog_df = _count_by_player(prog, "progressive_passes")
    key_df = _count_by_player(keyp, "key_passes")
    third_df = _count_by_player(third, "final_third_entries")

    summary = prog_df.merge(key_df, on=config.COL_PLAYER, how="outer")
    summary = summary.merge(third_df, on=config.COL_PLAYER, how="outer")
    summary = summary.fillna(0)

    for col in ["progressive_passes", "key_passes", "final_third_entries"]:
        if col in summary.columns:
            summary[col] = summary[col].astype(int)

    if not summary.empty:
        summary["total_impact_passes"] = (
            summary["progressive_passes"] +
            summary["key_passes"] +
            summary["final_third_entries"]
        )
        summary = summary.sort_values(
            ["total_impact_passes", "progressive_passes", "key_passes"],
            ascending=False
        ).reset_index(drop=True)

    return summary


# =========================================================
# FORMATION / POSITIONAL SHAPE
# =========================================================

def _get_touch_events(df):
    if df is None or df.empty:
        return pd.DataFrame()

    needed_cols = [config.COL_PLAYER, config.COL_X, config.COL_Y, config.COL_BEGIN]
    for col in needed_cols:
        if col not in df.columns:
            return pd.DataFrame()

    work = _prepare_event_df(df)
    work = _single_player_only(work)
    work = work.dropna(subset=[config.COL_PLAYER, config.COL_X, config.COL_Y, config.COL_BEGIN])

    return work.copy()


def _filter_time_window(df, start_min=None, end_min=None):
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if start_min is not None:
        work = work[work[config.COL_BEGIN] >= start_min * 60]

    if end_min is not None:
        work = work[work[config.COL_BEGIN] < end_min * 60]

    return work.copy()


def get_avg_positions(df, start_min=None, end_min=None, min_touches=2):
    touches = _get_touch_events(df)
    if touches.empty:
        return pd.DataFrame()

    touches = _filter_time_window(touches, start_min=start_min, end_min=end_min)

    if touches.empty:
        return pd.DataFrame()

    agg = (
        touches.groupby(config.COL_PLAYER)
        .agg(
            avg_x=(config.COL_X, "mean"),
            avg_y=(config.COL_Y, "mean"),
            touches=(config.COL_X, "size"),
            first_time=(config.COL_BEGIN, "min"),
        )
        .reset_index()
    )

    agg = agg[agg["touches"] >= min_touches].copy()
    if agg.empty:
        return agg

    agg = agg.sort_values(["avg_x", "avg_y"]).reset_index(drop=True)
    return agg


def _split_by_largest_gaps(values, n_splits=3):
    if len(values) <= 1:
        return [values]

    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    gap_idx = np.argsort(diffs)[::-1][:min(n_splits, len(diffs))]
    cut_points = sorted([idx + 1 for idx in gap_idx])

    groups = []
    start = 0
    for cp in cut_points:
        groups.append(values[start:cp])
        start = cp
    groups.append(values[start:])

    groups = [g for g in groups if len(g) > 0]
    return groups


def infer_formation_from_positions(pos_df):
    if pos_df is None or pos_df.empty:
        return "N/A"

    work = pos_df.sort_values("avg_x").reset_index(drop=True).copy()

    if len(work) < 7:
        return "N/A"

    outfield = work.iloc[1:].copy()

    if len(outfield) < 6:
        return "N/A"

    xs = outfield["avg_x"].tolist()

    groups4 = _split_by_largest_gaps(xs, n_splits=3)
    counts4 = [len(g) for g in groups4]

    if len(counts4) >= 3 and max(counts4) <= 5:
        return "-".join(str(c) for c in counts4)

    groups3 = _split_by_largest_gaps(xs, n_splits=2)
    counts3 = [len(g) for g in groups3]

    if len(counts3) >= 2:
        return "-".join(str(c) for c in counts3)

    return "N/A"


def create_positions_map(pos_df, title="Positions", subtitle=None):
    if pos_df is None or pos_df.empty:
        return None

    pitch = Pitch(
        pitch_type="custom",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#7bc67b",
        line_color="white",
        stripe=True
    )
    fig, ax = pitch.draw(figsize=(8, 11))
    fig.patch.set_facecolor("white")

    marker_sizes = 900 + (pos_df["touches"] / max(pos_df["touches"].max(), 1)) * 700

    pitch.scatter(
        pos_df["avg_x"],
        pos_df["avg_y"],
        s=marker_sizes,
        color="#1f5cff",
        edgecolors="white",
        linewidth=2,
        alpha=0.95,
        ax=ax,
        zorder=3
    )

    for _, row in pos_df.iterrows():
        ax.text(
            row["avg_x"],
            row["avg_y"],
            _player_display_name(row[config.COL_PLAYER]),
            color="white",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            zorder=4
        )

    if subtitle:
        ax.set_title(f"{title}\n{subtitle}", fontsize=14, color="black")
    else:
        ax.set_title(title, fontsize=14, color="black")

    return fig


def create_starting_shape_map(df, first_minutes=8, min_touches=2):
    pos_df = get_avg_positions(df, start_min=0, end_min=first_minutes, min_touches=min_touches)
    if pos_df.empty:
        return None, pos_df, "N/A"

    formation = infer_formation_from_positions(pos_df)
    subtitle = f"First {first_minutes} min | Inferred shape: {formation}"
    fig = create_positions_map(pos_df, title="Starting Shape", subtitle=subtitle)

    return fig, pos_df, formation


def get_match_max_minute(df):
    if df is None or df.empty or config.COL_BEGIN not in df.columns:
        return 0

    work = _prepare_event_df(df)
    if work.empty:
        return 0

    max_sec = work[config.COL_BEGIN].max()
    if pd.isna(max_sec):
        return 0

    return float(max_sec) / 60.0


def build_time_windows(df, window_size=15):
    max_min = get_match_max_minute(df)

    if max_min <= 0:
        return []

    windows = []
    start = 0
    while start < max_min:
        end = min(start + window_size, math.ceil(max_min))
        windows.append((start, end))
        start += window_size

    return windows


def create_time_window_maps(df, window_size=15, min_touches=2):
    windows = build_time_windows(df, window_size=window_size)
    outputs = []

    for start_min, end_min in windows:
        pos_df = get_avg_positions(df, start_min=start_min, end_min=end_min, min_touches=min_touches)

        if pos_df.empty:
            continue

        formation = infer_formation_from_positions(pos_df)
        subtitle = f"{int(start_min)}' - {int(end_min)}' | Shape: {formation}"
        fig = create_positions_map(pos_df, title="Time Window Shape", subtitle=subtitle)

        outputs.append({
            "start_min": start_min,
            "end_min": end_min,
            "formation": formation,
            "positions": pos_df,
            "fig": fig,
        })

    return outputs


def create_shape_summary_table(window_maps):
    if not window_maps:
        return pd.DataFrame(columns=["window", "shape", "players_shown"])

    rows = []
    for item in window_maps:
        rows.append({
            "window": f"{int(item['start_min'])}' - {int(item['end_min'])}'",
            "shape": item["formation"],
            "players_shown": len(item["positions"]),
        })

    return pd.DataFrame(rows)


# =========================================================
# PLAYER PIZZA
# =========================================================

def _count_touches_by_player(df):
    touches = _get_touch_events(df)
    if touches.empty:
        return pd.DataFrame(columns=[config.COL_PLAYER, "touches"])

    return touches.groupby(config.COL_PLAYER).size().reset_index(name="touches")


def _count_passes_by_player(df):
    work = _prepare_event_df(df)
    if work.empty:
        return pd.DataFrame(columns=[config.COL_PLAYER, "passes", "completed_passes"])

    passes = work[work.apply(_is_pass, axis=1)].copy()
    if passes.empty:
        return pd.DataFrame(columns=[config.COL_PLAYER, "passes", "completed_passes"])

    total_df = passes.groupby(config.COL_PLAYER).size().reset_index(name="passes")
    completed_df = passes[passes.apply(_is_complete_pass, axis=1)].groupby(config.COL_PLAYER).size().reset_index(name="completed_passes")

    out = total_df.merge(completed_df, on=config.COL_PLAYER, how="left")
    out["completed_passes"] = out["completed_passes"].fillna(0).astype(int)
    return out


def _count_shots_by_player(df):
    work = _prepare_event_df(df)
    if work.empty:
        return pd.DataFrame(columns=[config.COL_PLAYER, "shots"])

    shots = work[work.apply(_is_shot, axis=1)].copy()
    if shots.empty:
        return pd.DataFrame(columns=[config.COL_PLAYER, "shots"])

    return shots.groupby(config.COL_PLAYER).size().reset_index(name="shots")


def _count_df_by_player(dataframe, metric_name):
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=[config.COL_PLAYER, metric_name])

    return dataframe.groupby(config.COL_PLAYER).size().reset_index(name=metric_name)


def build_player_metrics_table(df):
    touches_df = _count_touches_by_player(df)
    passes_df = _count_passes_by_player(df)
    shots_df = _count_shots_by_player(df)
    prog_df = _count_df_by_player(get_progressive_passes(df), "progressive_passes")
    key_df = _count_df_by_player(get_key_passes(df), "key_passes")
    third_df = _count_df_by_player(get_final_third_entries(df), "final_third_entries")

    out = touches_df.merge(passes_df, on=config.COL_PLAYER, how="outer")
    out = out.merge(shots_df, on=config.COL_PLAYER, how="outer")
    out = out.merge(prog_df, on=config.COL_PLAYER, how="outer")
    out = out.merge(key_df, on=config.COL_PLAYER, how="outer")
    out = out.merge(third_df, on=config.COL_PLAYER, how="outer")

    if out.empty:
        return out

    out = out.fillna(0)

    int_cols = [
        "touches", "passes", "completed_passes", "shots",
        "progressive_passes", "key_passes", "final_third_entries"
    ]
    for col in int_cols:
        if col in out.columns:
            out[col] = out[col].astype(int)

    out["pass_accuracy"] = np.where(out["passes"] > 0, (out["completed_passes"] / out["passes"]) * 100, 0)
    out["progressive_pass_rate"] = np.where(out["passes"] > 0, (out["progressive_passes"] / out["passes"]) * 100, 0)
    out["key_pass_rate"] = np.where(out["passes"] > 0, (out["key_passes"] / out["passes"]) * 100, 0)

    out["impact_score"] = (
        out["progressive_passes"] * 2 +
        out["key_passes"] * 3 +
        out["final_third_entries"] * 2 +
        out["shots"] * 2 +
        out["completed_passes"] * 0.2 +
        out["touches"] * 0.05
    )

    out = out.sort_values(["impact_score", "touches"], ascending=False).reset_index(drop=True)
    return out


def _to_percentiles(series):
    """
    Convert numeric series to 0-100 percentile ranks within current dataframe.
    """
    if series.empty:
        return series

    ranks = series.rank(method="average", pct=True) * 100
    return ranks.round(0).astype(int)


def build_player_percentile_table(metrics_df):
    if metrics_df is None or metrics_df.empty:
        return pd.DataFrame()

    out = metrics_df.copy()

    metric_cols = [
        "touches",
        "passes",
        "completed_passes",
        "shots",
        "progressive_passes",
        "key_passes",
        "final_third_entries",
        "pass_accuracy",
        "progressive_pass_rate",
        "key_pass_rate",
    ]

    available = [c for c in metric_cols if c in out.columns]

    for col in available:
        out[f"{col}_pct"] = _to_percentiles(out[col])

    return out


def _pizza_param_config():
    return [
        ("Touches", "touches_pct", "#1f77b4"),
        ("Passes", "passes_pct", "#1f77b4"),
        ("Comp Pass", "completed_passes_pct", "#1f77b4"),
        ("Shots", "shots_pct", "#d62728"),
        ("Prog Pass", "progressive_passes_pct", "#ff7f0e"),
        ("Key Pass", "key_passes_pct", "#ff7f0e"),
        ("3rd Entries", "final_third_entries_pct", "#ff7f0e"),
        ("Pass Acc", "pass_accuracy_pct", "#2ca02c"),
        ("Prog Rate", "progressive_pass_rate_pct", "#9467bd"),
        ("Key Rate", "key_pass_rate_pct", "#9467bd"),
    ]


def create_player_pizza(player_row, team_name="Team"):
    if player_row is None or len(player_row) == 0:
        return None

    param_cfg = _pizza_param_config()
    params = [p[0] for p in param_cfg]
    values = [float(player_row.get(p[1], 0)) for p in param_cfg]
    slice_colors = [p[2] for p in param_cfg]

    baker = PyPizza(
        params=params,
        background_color="#f8f8f8",
        straight_line_color="#d9d9d9",
        straight_line_lw=1,
        last_circle_lw=1,
        other_circle_lw=1,
        other_circle_ls="-"
    )

    fig, ax = baker.make_pizza(
        values,
        figsize=(8, 8),
        color_blank_space="same",
        slice_colors=slice_colors,
        value_colors=["black"] * len(values),
        value_bck_colors=slice_colors,
        blank_alpha=0.35,
        kwargs_slices=dict(edgecolor="white", linewidth=1.2),
        kwargs_params=dict(color="black", fontsize=10),
        kwargs_values=dict(
            color="white",
            fontsize=9,
            bbox=dict(
                edgecolor="black",
                facecolor="black",
                boxstyle="round,pad=0.2",
                lw=0.5
            )
        )
    )

    player_name = str(player_row.get(config.COL_PLAYER, "Player"))
    ax.text(
        0,
        1.18,
        player_name,
        size=16,
        ha="center",
        va="center",
        weight="bold"
    )
    ax.text(
        0,
        1.08,
        f"{team_name} | Percentile Pizza",
        size=10,
        ha="center",
        va="center",
        color="dimgray"
    )

    return fig


def get_players_for_pizza(metrics_pct_df):
    if metrics_pct_df is None or metrics_pct_df.empty:
        return []

    return metrics_pct_df[config.COL_PLAYER].astype(str).tolist()


def paginate_players(players, page=1, per_page=4):
    if not players:
        return []

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    return players[start_idx:end_idx]


def get_total_pages(players, per_page=4):
    if not players:
        return 1
    return math.ceil(len(players) / per_page)


def get_pizza_page_rows(metrics_pct_df, page=1, per_page=4):
    players = get_players_for_pizza(metrics_pct_df)
    page_players = paginate_players(players, page=page, per_page=per_page)

    if not page_players:
        return pd.DataFrame()

    return metrics_pct_df[metrics_pct_df[config.COL_PLAYER].isin(page_players)].copy()