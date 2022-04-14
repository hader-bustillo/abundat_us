from scorestream import ss_url_requests

# change the locations in the script, to get the cities

locations = [[32.7767, -96.7970]]

radius = 50.0

complete_team_list = []
api_key = 'd572dff0-1e62-4f8d-962b-589bed0d6e24'

for latitude, longitude in locations:
    params = {
        'location' : {'latitude': latitude, 'longitude': longitude},
        'api_key': api_key,
        'distance': radius,
        'count': 10000
    }

    team_url = ss_url_requests.ss_url_requests(method='teams.search', method_key='method',
                                             params=params)
    team_list = team_url.make_request()

    team_list = team_list.json()

    if 'teamCollection' in team_list['result']['collections']:
        for each_team in team_list['result']['collections']['teamCollection']['list']:
            complete_team_list.append("{0},{1}".format(each_team['city'], each_team['state']))

        complete_team_list = list(set(complete_team_list))

        print("the team list for location " + repr(latitude) + repr(longitude) + "is \n" + repr(complete_team_list))

        complete_team_list = []
