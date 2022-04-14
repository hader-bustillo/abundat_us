import json
import requests
from scorestream import ss_integration



print("Started the games postback")
params = {
    "apiKey": "d572dff0-1e62-4f8d-962b-589bed0d6e24",
    "accessToken": "31ea2602-0123-476b-83bf-4b34da6261fd",
    "gamePostIds": [2674277],

}
result = ss_integration.get_complete_result(params=params,method='games.posts.get')
print(result)

