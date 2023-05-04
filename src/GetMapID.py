import requests
import config

url = 'https://maphub.net/api/1/map/list'

headers = {'Authorization': 'Token ' + config.MAPHUB_API_KEY}
r = requests.post(url, headers=headers)

map_title = input('Copy-paste the map title: ')

maps = r.json()
found = False
for m in maps['owner']:
    if m['title'] == map_title:
        found = True
        print(m['id'])
        break

if not found:
    print('Map not found. Make sure your title is exact.')
