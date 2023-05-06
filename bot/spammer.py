import json
import time

import requests

counter = 0

url = "https://discord.com/api/v9/channels/1102307616685830316/messages"

payload = json.dumps({"content": "a"})
headers = {'Authorization': 'Njk4OTI0ODE5MDA1MzA4OTc4.Gt3X2t.Oa5_jLDdb3kl5DbOOGDmLY7i7rZkOt4WSrTU74',
           'Content-Type': 'application/json',
           'Cookie': '__dcfduid=60b13e747af511ecb1d8beadd4b852b7; __sdcfduid=60b13e747af511ecb1d8beadd4b852b78f27c5884b1e654a10633ae3550bd536a31789f4a54e8aeae8f43f889c2306e5'}

for _ in range(100000000):
    response = requests.request("POST", url, headers=headers, data=payload)
    j = json.loads(response.text)
    try:
        if j["code"] == 20028:
            time.sleep(j["retry_after"] * 2)
    except KeyError:
        pass
    print(response.text)
