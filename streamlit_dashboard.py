import streamlit as st
import pandas as pd
from utils_streamlit import prep_df, calc_expected_points
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="RASO",
 layout="wide")

pd.set_option("display.float_format", lambda x: "%.3f" % x)

# Title
st.title('Fantasy Premier League Dashboard')

# Create Tabs
position_breakdown , fixtures, player_comparison = st.tabs(["Position Breakdown",
 'Fixtures',
 'Player Comparison'])

# load team data
team_data = pd.read_csv('./data/teams_20230718_081225.csv')

with position_breakdown:
 # Load the data (replace with the path to your data file)
 df = pd.read_csv('data/players_20230718_081225.csv')
 df = prep_df(df)

 budget = 2000


 # Sidebar with team selection

 selected_position = st.selectbox('Select your team', df['position'].unique())

 # Filter the data for the selected team
 pos_data = df[df['position'] == selected_position]


 # Display player performance
 st.header('Player Performance Totals')
 st.dataframe(pos_data[['player', 'now_cost','total_points','minutes', 'goals_scored',
 'assists', 'clean_sheets', 'goals_conceded', 'own_goals',
 'penalties_saved', 'penalties_missed', 'yellow_cards', 'red_cards',
 'saves', 'bonus', 'bps', 'influence', 'creativity', 'threat',
 'ict_index', 'starts', 'expected_goals', 'expected_assists',
 'expected_goal_involvements']])


 expected = pos_data[['player', 'now_cost','element_type','points_per_game',
 'expected_goals',
 'expected_assists',
 'expected_goals_per_90', 'saves_per_90', 'expected_assists_per_90',
 'expected_goal_involvements_per_90', 'expected_goals_conceded_per_90',
 'goals_conceded_per_90','starts_per_90', 'clean_sheets_per_90']]
 expected = calc_expected_points(expected)

 st.write('Average points per player:', expected)

 per_dollar = pos_data.copy()
 per_dollar['points_per_dollar'] = per_dollar['points_per_game'] / per_dollar['now_cost']
 st.write('Expected points per dollar:', per_dollar[['player','points_per_dollar','now_cost',
 'points_per_game', 'element_type']])


 # Display player availability
 st.header('Player Availability')
 st.write('Injured players:', pos_data[pos_data['status'] == 'injured']['player'])
 st.write('Suspended players:', pos_data[pos_data['status'] == 'suspended']['player'])


with player_comparison:
 # Load the data (replace with the path to your data file)
 df = pd.read_csv('data/players_20230718_081225.csv')
 df = prep_df(df)

 # choose a set of players to compare , unlimited
 player_list = st.multiselect('Select players to compare', df['player'].unique())
 selected_players = df[df['player'].isin(player_list)]
 st.write(selected_players[['player', 'now_cost','total_points','minutes', 'goals_scored',
 'assists', 'clean_sheets', 'goals_conceded']])
 expected = selected_players[['player', 'now_cost', 'element_type', 'points_per_game',
 'expected_goals',
 'expected_assists',
 'expected_goals_per_90', 'saves_per_90', 'expected_assists_per_90',
 'expected_goal_involvements_per_90', 'expected_goals_conceded_per_90',
 'goals_conceded_per_90', 'starts_per_90', 'clean_sheets_per_90']]
 expected = calc_expected_points(expected)
 st.dataframe(expected)

with fixtures:
 fixtures = pd.read_csv('./data/fixtures_20230718_081225.csv')
 fixtures = fixtures[['id','team_a','team_h','team_h_difficulty','team_a_difficulty']]
 # display
 st.write('Next N fixtures by difficulty')
 # create a select box that creceives a number of fixtures default 10
 number_of_fixtures = st.selectbox('Select number of fixtures', [10,2,3,4,5,6,7,8,9,38] )


 l_fixtures_per_all_teams = []
 l_difficulty_per_all_teams = []
 for team in fixtures['team_h'].unique():
  a = fixtures[(fixtures['team_h'] == team) | (fixtures['team_a'] == team)]
  a['current_team'] = team

  # the other value that isnt team from the set team_a and team_h
  a['opposing_team'] = a.apply(lambda x: x['team_a'] if x['team_h'] == team else x['team_h'], axis=1)
  a['opposing_team_difficulty'] = a.apply(lambda x: x['team_h_difficulty'] if x['team_h'] == team else x['team_a_difficulty'], axis=1)

  # create a row of the fixtures
  row_of_fixtures = a['opposing_team'].values[:number_of_fixtures+1]
  row_of_difficulties = a['opposing_team_difficulty'].values[:number_of_fixtures+1]

  l_fixtures_per_all_teams.append([team] + list(row_of_fixtures))
  l_difficulty_per_all_teams.append([team] + list(row_of_difficulties))
 cols_for_df = ['Team_Name'] + list(range(1, number_of_fixtures + 2))
 df_fixtures_filtered = pd.DataFrame(l_fixtures_per_all_teams, columns= cols_for_df)
 df_rows_difficulty = pd.DataFrame(l_difficulty_per_all_teams, columns= cols_for_df)

 # replace team id with team name
 #create dictionary of team id and team name
 convert_team_id_dict = {}
 for ix,row in team_data.iterrows():
  convert_team_id_dict[row['id']]= row['short_name']

 # create team id to difficulty dictionary
 team_to_difficulty_dict = {}
 for team in fixtures['team_a'].unique():
  team_name = convert_team_id_dict[team]
  team_to_difficulty_dict[team_name] = fixtures[fixtures['team_a'] == team]['team_h_difficulty'].values[0]


 # convert df_fixtures_filtered from all cells from id to value using dict

 df_fixtures_filtered = df_fixtures_filtered.replace(convert_team_id_dict)
 #convert team_Name column in df_rows_difficulty using the dictionary
 df_rows_difficulty['Team_Name'] = df_rows_difficulty['Team_Name'].replace(convert_team_id_dict)
 df_rows_difficulty = df_rows_difficulty.set_index('Team_Name')
 n_cols = len(df_rows_difficulty.columns)
 df_rows_difficulty['AVG_Difficulty'] = df_rows_difficulty[df_rows_difficulty.columns[1:n_cols]].mean(axis=1)
 df_rows_difficulty['STDev'] = df_rows_difficulty[df_rows_difficulty.columns[1:n_cols]].std(axis=1)
 st.dataframe(df_rows_difficulty)


 # Function to determine the background color based on cell position
 def get_background_color(value,team_to_difficulty_dict):
     # create a dictionary of difficulty and color
     gradient_colors = {
     1: '#00FF00', # Green
     2: '#80FF80', # Light Green
     3: '#FFFF00', # Yellow
     4: '#FFA500', # Orange
     5: '#FF0000' # Red
     }
     difficulty_per_row = team_to_difficulty_dict[value]
     return gradient_colors[difficulty_per_row]


 # apply the function to all elements of all columns except the first one
 df_new = df_fixtures_filtered.set_index('Team_Name')

 # Apply the background color to each cell
 styled_df = df_new.style.applymap(lambda x: f'background-color: {get_background_color(x,team_to_difficulty_dict)}')

 # Display the styled DataFrame
 st.dataframe(styled_df)
