import streamlit as st
import config
import utils

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="wide"
)

st.title(f"{config.PAGE_ICON} {config.PAGE_TITLE}")

# =========================================================
# LOAD DATA
# =========================================================
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "csv"])

if uploaded_file is not None:
    df = utils.load_and_clean_data(uploaded_file)
    missing_cols = utils.validate_columns(df)
    if missing_cols:
        st.error(f"Missing columns: {missing_cols}")
        st.stop()
else:
    st.warning("Please upload a data file")
    st.stop()

# =========================================================
# SIDEBAR FILTERS
# =========================================================
st.sidebar.header("⚙️ Filters")

teams = ["All"] + sorted(df[config.COL_TEAM].dropna().astype(str).unique().tolist())
selected_team = st.sidebar.selectbox("Select Team:", teams)

if selected_team != "All":
    team_df = df[df[config.COL_TEAM].astype(str) == selected_team]
else:
    team_df = df

players = ["All"] + sorted(team_df[config.COL_PLAYER].dropna().astype(str).unique().tolist())
selected_player = st.sidebar.selectbox("Select Player:", players)

st.sidebar.markdown("---")
st.sidebar.subheader("Shape Settings")

starting_minutes = st.sidebar.slider("Starting shape minutes", min_value=4, max_value=15, value=8, step=1)
window_size = st.sidebar.slider("Time window size (min)", min_value=5, max_value=20, value=15, step=5)
min_touches_shape = st.sidebar.slider("Min touches for shape", min_value=1, max_value=5, value=2, step=1)

st.sidebar.markdown("---")
st.sidebar.subheader("Pizza Settings")
pizza_per_page = st.sidebar.selectbox("Players per pizza page", [4, 5], index=0)

# =========================================================
# APPLY FILTERS
# =========================================================
filtered_df = df.copy()

if selected_team != "All":
    filtered_df = filtered_df[filtered_df[config.COL_TEAM].astype(str) == selected_team]

if selected_player != "All":
    filtered_df = filtered_df[filtered_df[config.COL_PLAYER].astype(str) == selected_player]

# =========================================================
# HEADER
# =========================================================
st.subheader(f"📍 Analysis: Team = {selected_team} | Player = {selected_player}")

# =========================================================
# METRICS
# =========================================================
st.markdown("## 📊 Match Stats")

total_events, total_passes, total_shots = utils.calculate_metrics(filtered_df)

m1, m2, m3 = st.columns(3)
m1.metric("Total Events", total_events)
m2.metric("Total Passes", total_passes)
m3.metric("Total Shots", total_shots)

st.markdown("---")

# =========================================================
# PASS NETWORK
# =========================================================
st.markdown("## 🕸️ Pass Network")

if selected_player != "All":
    st.info("Pass Network is best viewed on full team selection. اختر الفريق فقط بدون لاعب.")
else:
    fig_network, edge_df = utils.create_pass_network(filtered_df, min_pass_count=2, max_distance=10)

    if fig_network:
        st.pyplot(fig_network, use_container_width=True)

        if edge_df is not None and not edge_df.empty:
            st.markdown("### Top Connections")
            st.dataframe(edge_df.head(10), use_container_width=True)
    else:
        st.info("No pass network could be inferred from the available data.")

st.markdown("---")

# =========================================================
# ADVANCED PASSING
# =========================================================
st.markdown("## 🚀 Advanced Passing Analysis")

summary_df = utils.create_advanced_passing_summary(filtered_df)

c1, c2, c3 = st.columns(3)

prog_count = 0
key_count = 0
third_count = 0

if not summary_df.empty:
    prog_count = int(summary_df["progressive_passes"].sum())
    key_count = int(summary_df["key_passes"].sum())
    third_count = int(summary_df["final_third_entries"].sum())

c1.metric("Progressive Passes", prog_count)
c2.metric("Key Passes", key_count)
c3.metric("Final Third Entries", third_count)

colA, colB = st.columns(2)

with colA:
    st.markdown("### 🔷 Progressive Passes")
    fig_prog, prog_df = utils.create_progressive_passes_map(filtered_df)
    if fig_prog:
        st.pyplot(fig_prog, use_container_width=True)
    else:
        st.info("No progressive passes found.")

with colB:
    st.markdown("### 🔴 Key Passes")
    fig_key, key_df = utils.create_key_passes_map(filtered_df)
    if fig_key:
        st.pyplot(fig_key, use_container_width=True)
    else:
        st.info("No key passes found.")

st.markdown("### 🟣 Final Third Entries")
fig_third, third_df = utils.create_final_third_entries_map(filtered_df)
if fig_third:
    st.pyplot(fig_third, use_container_width=True)
else:
    st.info("No final third entries found.")

if not summary_df.empty:
    st.markdown("### Player Impact Table")
    st.dataframe(summary_df, use_container_width=True)

st.markdown("---")

# =========================================================
# STARTING SHAPE + TIME CHANGES
# =========================================================
st.markdown("## 🧭 Team Shape & Time Changes")

if selected_player != "All":
    st.info("Shape analysis is best viewed on full team selection. اختر الفريق فقط بدون لاعب.")
else:
    fig_start, start_pos_df, start_shape = utils.create_starting_shape_map(
        filtered_df,
        first_minutes=starting_minutes,
        min_touches=min_touches_shape
    )

    if fig_start:
        s1, s2 = st.columns([2, 1])

        with s1:
            st.markdown("### Starting Shape")
            st.pyplot(fig_start, use_container_width=True)

        with s2:
            st.markdown("### Starting Shape Summary")
            st.metric("Inferred Shape", start_shape)
            st.metric("Players Shown", len(start_pos_df))
            st.dataframe(
                start_pos_df[[config.COL_PLAYER, "avg_x", "avg_y", "touches"]]
                .sort_values("avg_x"),
                use_container_width=True
            )
    else:
        st.info("No starting shape could be inferred.")

    st.markdown("### Time Window Position Changes")

    window_maps = utils.create_time_window_maps(
        filtered_df,
        window_size=window_size,
        min_touches=min_touches_shape
    )

    if window_maps:
        summary_shapes = utils.create_shape_summary_table(window_maps)
        st.dataframe(summary_shapes, use_container_width=True)

        for i in range(0, len(window_maps), 2):
            cols = st.columns(2)

            item_left = window_maps[i]
            with cols[0]:
                st.pyplot(item_left["fig"], use_container_width=True)

            if i + 1 < len(window_maps):
                item_right = window_maps[i + 1]
                with cols[1]:
                    st.pyplot(item_right["fig"], use_container_width=True)
    else:
        st.info("No time window shape maps could be created.")

    st.caption("Note: these are inferred positional shapes by time windows, not official substitution events.")

st.markdown("---")

# =========================================================
# PLAYER PIZZA PAGES
# =========================================================
st.markdown("## 🍕 Player Pizza Pages")

if selected_player != "All":
    st.info("Pizza pages are best viewed on full team selection. اختر الفريق فقط بدون لاعب.")
else:
    metrics_df = utils.build_player_metrics_table(filtered_df)

    if metrics_df.empty:
        st.info("No player metrics available for pizza charts.")
    else:
        metrics_pct_df = utils.build_player_percentile_table(metrics_df)
        player_list = utils.get_players_for_pizza(metrics_pct_df)
        total_pages = utils.get_total_pages(player_list, per_page=pizza_per_page)

        page_col1, page_col2, page_col3 = st.columns([1, 1, 2])
        with page_col1:
            pizza_page = st.number_input(
                "Pizza Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1
            )
        with page_col2:
            st.metric("Total Pages", total_pages)
        with page_col3:
            st.write(f"Showing {pizza_per_page} players per page")

        page_df = utils.get_pizza_page_rows(metrics_pct_df, page=pizza_page, per_page=pizza_per_page)

        if page_df.empty:
            st.info("No players found for this pizza page.")
        else:
            page_df = page_df.reset_index(drop=True)

            for i in range(0, len(page_df), 2):
                cols = st.columns(2)

                left_row = page_df.iloc[i]
                with cols[0]:
                    fig_left = utils.create_player_pizza(left_row, team_name=selected_team)
                    if fig_left:
                        st.pyplot(fig_left, use_container_width=True)

                if i + 1 < len(page_df):
                    right_row = page_df.iloc[i + 1]
                    with cols[1]:
                        fig_right = utils.create_player_pizza(right_row, team_name=selected_team)
                        if fig_right:
                            st.pyplot(fig_right, use_container_width=True)

            st.markdown("### Pizza Metrics Table")
            show_cols = [
                config.COL_PLAYER,
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
                "impact_score",
            ]
            show_cols = [c for c in show_cols if c in page_df.columns]
            st.dataframe(page_df[show_cols], use_container_width=True)

st.markdown("---")

# =========================================================
# BASIC VISUALS
# =========================================================
st.markdown("## 📍 Visual Analysis")

colC, colD = st.columns(2)

with colC:
    st.markdown("### 🔵 Pass Map")
    fig_pass = utils.create_pass_map(filtered_df)
    if fig_pass:
        st.pyplot(fig_pass, use_container_width=True)
    else:
        st.info("No pass data available")

with colD:
    st.markdown("### 🔥 Heatmap")
    fig_heat = utils.create_heatmap(filtered_df)
    if fig_heat:
        st.pyplot(fig_heat, use_container_width=True)
    else:
        st.info("No positional data")

st.markdown("### 🟡 Shot Map")
fig_shot = utils.create_shot_map(filtered_df)
if fig_shot:
    st.pyplot(fig_shot, use_container_width=True)
else:
    st.info("No shot data available")

st.markdown("---")

# =========================================================
# RAW DATA
# =========================================================
with st.expander("📄 Show Raw Data"):
    st.dataframe(filtered_df, use_container_width=True)