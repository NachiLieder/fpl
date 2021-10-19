# https://medium.com/analytics-vidhya/getting-started-with-fantasy-premier-league-data-56d3b9be8c32

import requests
import pandas as pd
import numpy as np
from pprint import pprint


# base url for all FPL API endpoints

base_url = 'https://fantasy.premierleague.com/api/'

# get data from bootstrap-static endpoint
r = requests.get(base_url+'bootstrap-static/').json()

# show the top level fields
pprint(r, indent=2, depth=1, compact=True)
# get player data from 'elements' field
players = r['elements']

# show data for first player
pprint(players[0])


pd.set_option('display.max_columns', None)

# create players dataframe
players = pd.json_normalize(r['elements'])

# show some information about first five players
players[['id', 'web_name', 'team', 'element_type']].head()

# create teams dataframe
teams = pd.json_normalize(r['teams'])


# get position information from 'element_types' field
positions = pd.json_normalize(r['element_types'])



# join players to teams
df = pd.merge(
    left=players,
    right=teams,
    left_on='team',
    right_on='id'
)

# show joined result
df[['first_name', 'second_name', 'name']].head()

# join player positions
df = df.merge(
    positions,
    left_on='element_type',
    right_on='id'
)

# rename columns
df = df.rename(
    columns={'name':'team_name', 'singular_name':'position_name'}
)


##################################
# get data from 'element-summary/{PID}/' endpoint for PID=4
r = requests.get(base_url + 'element-summary/4/').json()

# show top-level fields for player summary
pprint(r, depth=1)
# show data for first gameweek
pprint(r['history'][0])


def get_gameweek_history(player_id):
    '''get all gameweek info for a given player_id'''

    # send GET request to
    # https://fantasy.premierleague.com/api/element-summary/{PID}/
    r = requests.get(
        base_url + 'element-summary/' + str(player_id) + '/'
    ).json()

    # extract 'history' data from response into dataframe
    df = pd.json_normalize(r['history'])

    return df


def get_season_history(player_id):
    '''get all past season info for a given player_id'''

    # send GET request to
    # https://fantasy.premierleague.com/api/element-summary/{PID}/
    r = requests.get(
        base_url + 'element-summary/' + str(player_id) + '/'
    ).json()

    # extract 'history_past' data from response into dataframe
    df = pd.json_normalize(r['history_past'])

    return df


# show player #4's gameweek history
get_gameweek_history(4)[
    [
        'round',
        'total_points',
        'minutes',
        'goals_scored',
        'assists'
    ]
].head()

# full_gw_hist = pd.DataFrame()
# for p_id in players['id']:
#     single_gw_hist = get_gameweek_history(p_id)
#     full_gw_hist = full_gw_hist.append(single_gw_hist)
# full_gw_hist
# full_gw_hist_with_name = full_gw_hist.merge(players[['id','team','web_name','element_type']], how='inner', left_on='element', right_on = 'id')
# full_gw_hist_with_name.to_csv('full_gw_hist_with_name.csv')



# select columns of interest from players df
players = players[
    ['id', 'first_name', 'second_name', 'web_name', 'team',
     'element_type']
]

# join team name
players = players.merge(
    teams[['id', 'name']],
    left_on='team',
    right_on='id',
    suffixes=['_player', None]
).drop(['team', 'id'], axis=1)

# join player positions
players = players.merge(
    positions[['id', 'singular_name_short']],
    left_on='element_type',
    right_on='id'
).drop(['element_type', 'id'], axis=1)

players.head()


from tqdm.auto import tqdm
tqdm.pandas()
# get gameweek histories for each player
points = players['id_player'].progress_apply(get_gameweek_history)

# combine results into single dataframe
points = pd.concat(df for df in points)

# join web_name
points = players[['id_player', 'web_name','singular_name_short', 'first_name', 'second_name']].merge(
    points,
    left_on='id_player',
    right_on='element'
)

points.to_csv('points.csv')
