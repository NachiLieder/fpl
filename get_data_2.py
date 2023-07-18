import requests
import pandas as pd
import json

# Make a request to GET the data from the FPL API
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
response = requests.get(url)

# Convert JSON data to a python object
data = json.loads(response.text)

# Create pandas DataFrame from JSON player data
dataset = pd.DataFrame.from_dict(data['elements'])

timestamp_now = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
dataset.to_csv(f'./data/players_{timestamp_now}.csv', index=False)


# get teams data
teams = pd.DataFrame(data['teams'])
teams.to_csv(f'./data/teams_{timestamp_now}.csv', index=False)

### get fixtures
url = 'https://fantasy.premierleague.com/api/fixtures/'
response = requests.get(url)

# Convert JSON data to a python object
data = json.loads(response.text)

fixtures = pd.DataFrame.from_dict(data)
fixtures.to_csv(f'./data/fixtures_{timestamp_now}.csv', index=False)

# get also the  player data
print()
