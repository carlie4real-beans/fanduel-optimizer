import streamlit as st
import pandas as pd
import pulp
import numpy as np
import io

st.set_page_config(page_title="FD Multi-Optimizer", page_icon="🏈", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 50px; border-radius: 10px; font-size: 16px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; height: 50px; border-radius: 10px; background-color: #00875A !important; color: white; }
    input { min-height: 44px; }
    div[data-testid="stMetricValue"] { font-size: 24px; }
    </style>
""", unsafe_allow_html=True)

st.title("🏈 Mobile FanDuel Multi-Optimizer")
st.write("Generate multiple unique, high-upside tournament lineups right from your phone.")

sample_data = [
    {"Player": "Lamar Jackson", "Position": "QB", "Team": "BAL", "Salary": 8800, "Projection": 22.4, "StdDev": 4.5},
    {"Player": "Jayden Daniels", "Position": "QB", "Team": "WAS", "Salary": 8200, "Projection": 20.1, "StdDev": 4.2},
    {"Player": "Saquon Barkley", "Position": "RB", "Team": "PHI", "Salary": 9200, "Projection": 19.1, "StdDev": 4.4},
    {"Player": "Derrick Henry", "Position": "RB", "Team": "BAL", "Salary": 8600, "Projection": 18.5, "StdDev": 4.3},
    {"Player": "Breece Hall", "Position": "RB", "Team": "NYJ", "Salary": 8000, "Projection": 16.8, "StdDev": 4.0},
    {"Player": "Justin Jefferson", "Position": "WR", "Team": "MIN", "Salary": 9000, "Projection": 17.8, "StdDev": 4.5},
    {"Player": "Zay Flowers", "Position": "WR", "Team": "BAL", "Salary": 7100, "Projection": 13.2, "StdDev": 3.3},
    {"Player": "Nico Collins", "Position": "WR", "Team": "HOU", "Salary": 7800, "Projection": 14.6, "StdDev": 3.7},
    {"Player": "Terry McLaurin", "Position": "WR", "Team": "WAS", "Salary": 6800, "Projection": 12.4, "StdDev": 3.1},
    {"Player": "George Kittle", "Position": "TE", "Team": "SF", "Salary": 6600, "Projection": 11.8, "StdDev": 3.0},
    {"Player": "Zach Ertz", "Position": "TE", "Team": "WAS", "Salary": 5100, "Projection": 8.9, "StdDev": 2.1},
    {"Player": "Vikings D", "Position": "D", "Team": "MIN", "Salary": 4300, "Projection": 8.1, "StdDev": 1.9},
    {"Player": "Commanders D", "Position": "D", "Team": "WAS", "Salary": 3800, "Projection": 6.8, "StdDev": 1.7}
]

uploaded_file = st.file_uploader("📥 Upload FanDuel Slate CSV", type=["csv"])
df_pool = pd.read_csv(uploaded_file) if uploaded_file else pd.DataFrame(sample_data)

if 'StdDev' not in df_pool.columns:
    df_pool['StdDev'] = df_pool['Projection'] * 0.25

with st.expander("⚙️ Roster Controls & Multi-Lineup Settings", expanded=True):
    all_players = df_pool['Player'].tolist()
    lock_selection = st.multiselect("🔒 Lock Players", all_players)
    exclude_selection = st.multiselect("❌ Exclude Players", all_players)
    num_lineups = st.slider("📋 Number of Lineups to Generate", min_value=1, max_value=20, value=5)
    uniqueness = st.slider("🔄 Min Player Differences Between Lineups", min_value=1, max_value=4, value=3)

def generate_multi_lineups(df, num_lineups, uniqueness, locked=[], excluded=[]):
    if excluded:
        df = df[~df['Player'].isin(excluded)]
    iterations = 1000
    sim_results = np.zeros((len(df), iterations))
    for idx, row in enumerate(df.itertuples()):
        sim_results[idx] = np.random.normal(row.Projection, row.StdDev, iterations)
    df['Ceiling'] = np.percentile(sim_results, 85, axis=1)
    
    saved_lineups = []
    past_lineup_masks = []

    for n in range(num_lineups):
        prob = pulp.LpProblem(f"FD_Multi_{n}", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("P", df.index, cat='Binary')
        
        prob += pulp.lpSum(df.loc[i, 'Ceiling'] * player_vars[i] for i in df.index)
        prob += pulp.lpSum(df.loc[i, 'Salary'] * player_vars[i] for i in df.index) <= 60000
        prob += pulp.lpSum(player_vars[i] for i in df.index) == 9
        
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'QB') == 1
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'D') == 1
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'RB') >= 2
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'RB') <= 3
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'WR') >= 3
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'WR') <= 4
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'TE') >= 1
        prob += pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'TE') <= 2
        
        if locked:
            for i in df.index:
                if df.loc[i, 'Player'] in locked: prob += player_vars[i] == 1

        for team in df['Team'].unique():
            qb = pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] == 'QB' and df.loc[i, 'Team'] == team)
            targets = pulp.lpSum(player_vars[i] for i in df.index if df.loc[i, 'Position'] in ['WR', 'TE'] and df.loc[i, 'Team'] == team)
            prob += targets >= qb

        for past_mask in past_lineup_masks:
            prob += pulp.lpSum(player_vars[i] for i in df.index if past_mask[i] == 1) <= (9 - uniqueness)

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] == "Optimal":
            current_mask = {i: int(player_vars[i].varValue == 1) for i in df.index}
            past_lineup_masks.append(current_mask)
            lineup_df = df[[player_vars[i].varValue == 1 for i in df.index]].copy()
            lineup_df['Lineup_Num'] = n + 1
            saved_lineups.append(lineup_df)
        else:
            break
            
    return saved_lineups

if st.button("🚀 Generate Multi-Entry Lineups"):
    with st.spinner("Executing mathematical simulation loops..."):
        all_lineups = generate_multi_lineups(df_pool, num_lineups, uniqueness, lock_selection, exclude_selection)
        if all_lineups:
            st.success(f"🏆 Successfully generated {len(all_lineups)} unique tournament lineups!")
            final_export_df = pd.concat(all_lineups)
            tabs = st.tabs([f"Lineup #{i+1}" for i in range(len(all_lineups))])
            for idx, tab in enumerate(tabs):
                with tab:
                    l_df = all_lineups[idx]
                    col1, col2 = st.columns(2)
                    col1.metric("Total Salary", f"${l_df['Salary'].sum():,}")
                    col2.metric("Proj. Ceiling", f"{l_df['Ceiling'].sum():.1f}")
                    st.dataframe(l_df[['Player', 'Position', 'Team', 'Salary']], use_container_width=True, hide_index=True)
            csv_buffer = io.StringIO()
            final_export_df.to_csv(csv_buffer, index=False)
            st.markdown("---")
            st.download_button(label="💾 Download Multi-Lineup Upload CSV", data=csv_buffer.getvalue(), file_name="fd_multi_upload.csv", mime="text/csv")
        else:
            st.error("Could not generate configurations.")
