import streamlit as st
import pandas as pd

def prep_df(df):
 df['player'] = df['web_name']
 element_dict = {1:'GK',
 2: 'DEF',
 3:'MID',
 4: 'FWD'}
 df['position'] = df['element_type'].apply(lambda x: element_dict[x])
 return df

def calc_expected_points(expected):
 # Create a new column 'expected_points' in the 'expected' DataFrame
 expected['expected_points'] = 0

 # Calculate expected points for players with element type = 1
 element_type_1_mask = expected['element_type'] == 1
 expected.loc[element_type_1_mask, 'expected_points'] = (
 4 * expected.loc[element_type_1_mask, 'clean_sheets_per_90'] +
 -1 * (expected.loc[element_type_1_mask, 'goals_conceded_per_90'] / 2) +
 1 * (expected.loc[element_type_1_mask, 'saves_per_90'] / 4)
 )

 # Calculate expected points for players with element type = 2
 element_type_2_mask = expected['element_type'] == 2
 expected.loc[element_type_2_mask, 'expected_points'] = (
 4 * expected.loc[element_type_2_mask, 'clean_sheets_per_90'] +
 -1 * (expected.loc[element_type_2_mask, 'goals_conceded_per_90'] / 2) +
 6 * expected.loc[element_type_2_mask, 'expected_goals_per_90'] +
 3 * expected.loc[element_type_2_mask, 'expected_assists_per_90']
 )

 # Calculate expected points for players with element type = 3
 element_type_3_mask = expected['element_type'] == 3
 expected.loc[element_type_3_mask, 'expected_points'] = (
 1 * expected.loc[element_type_3_mask, 'clean_sheets_per_90'] +
 5 * expected.loc[element_type_3_mask, 'expected_goals_per_90'] +
 3 * expected.loc[element_type_3_mask, 'expected_assists_per_90']
 )

 # Calculate expected points for players with element type = 4
 element_type_4_mask = expected['element_type'] == 4
 expected.loc[element_type_4_mask, 'expected_points'] = (
 4 * expected.loc[element_type_4_mask, 'expected_goals_per_90'] +
 3 * expected.loc[element_type_4_mask, 'expected_assists_per_90']
 )
 return expected
