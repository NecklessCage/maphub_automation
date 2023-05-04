
from tqdm import tqdm
from glob import glob
from pathlib import Path
import json
import requests
import pandas as pd
import geopandas as gp
import config


# # Load Data
#
df = pd.read_excel('../data/data.xlsx', sheet_name='maphub')
df.head()


# # Upload Images and Icons
#
def upload_image_marker(kind, file_path):
    file_path = Path(file_path)
    # path where we store the info JSON
    info_json = file_path.parent / f'{file_path.stem}.json'

    # if the JSON file exists, the image/marker is already uploaded, skip the upload
    if info_json.is_file():
        print(f'Skipping {kind} {file_path.name}')
        return

    url = f'https://maphub.net/api/1/{kind}/upload'

    # use the file's extension as file_type
    args = {
        'file_type': file_path.suffix[1:],
    }

    headers = {
        'Authorization': 'Token ' + config.MAPHUB_API_KEY,
        'MapHub-API-Arg': json.dumps(args),
    }

    with open(file_path, 'rb') as f:
        # the upload request
        res = requests.post(url, headers=headers, data=f)
        data = res.json()

    # check that upload was successful, if not print error
    if f'{kind}_id' not in data:
        print(data['error'])
        return

    # save the image_info dict to disk
    with open(info_json, 'w') as f:
        json.dump(data, f, indent=2)


# Upload Images
for file_path in tqdm(glob('../img/*.png') + glob('../img/*.jpeg') + glob('../img/*.jpg')):
    print(f'Processing {file_path}')
    upload_image_marker('image', file_path)

# Upload Icons
for file_path in tqdm(glob('../icons/*')):
    print(f'Processing {file_path}')
    upload_image_marker('marker', file_path)


# # Prepare Image and Icon Columns
#


key_map = {
    'image_id': 'id',
    'height': 'h',
    'width': 'w'
}


def load_json(file_name, type):
    try:
        match type:
            case 'image':
                with open(f'../img/{file_name}.json', 'r') as f:
                    return {key_map[k] if k in key_map else k: v
                            for k, v in json.load(f).items() if v is not None}
            case 'icon':
                with open(f'../icons/{file_name}.json', 'r') as f:
                    return json.load(f)['marker_id']
            case _:
                raise Exception('Invalid type')
    except FileNotFoundError:
        return None


df['image'] = [load_json(i, 'image') for i in df.id]
df['marker_id'] = [load_json(i, 'icon') for i in df.icon_name]
df.drop(columns='icon_name', inplace=True)
df.head()


# # Prepare Group Data
group_names = df.group_name.unique()
group_map = {k: i for i, k in enumerate(df.group_name.unique(), start=1001)}
print(group_map)
df['group'] = [group_map[g] for g in df.group_name]
groups = [
    {
        'id': i,
        'title': t,
    } for t, i in group_map.items()
]

# # Remove Unnecessary Columns
df.drop(columns=['group_name', 'id', 'marker_color'], inplace=True)


# # Prepare `geojson`
gdf = gp.GeoDataFrame(df, geometry=gp.points_from_xy(
    df.longitude, df.latitude))  # Note the order is lnglat
gdf = gdf.drop(columns=['longitude', 'latitude'])


SMALL_ICON_ZOOM_LEVEL = 6
geo_json = json.loads(gdf.to_json(drop_id=True))
geo_json['properties'] = {'simplify': SMALL_ICON_ZOOM_LEVEL}
geo_json['groups'] = groups


# # Update Map
def update_map(geo_json, map_id):
    url = 'https://maphub.net/api/1/map/update'
    args = {
        'map_id': map_id,
        'geojson': geo_json,
        'title': config.MAP_TITLE,
        'basemap': 'mapbox-streets_satellite',
        'description': config.MAP_DESCRIPTION,
        'visibility': 'public',
    }
    headers = {
        'Authorization': 'Token ' + config.MAPHUB_API_KEY,
    }

    res = requests.post(url, json=args, headers=headers)
    data = res.json()

    if 'id' not in data:
        print(data['error'])
    else:
        print('Map updated')
        print(config.MAPHUB_MAP_ID)
    return data


confirmation = input(
    f'Are you sure you want to update the ENTIRE map on MapHub, ID={config.MAPHUB_MAP_ID}? YES/N: ')
print(f'{confirmation = }')
if confirmation == 'YES':
    print('Updating Map...')
    res = update_map(geo_json, config.MAPHUB_MAP_ID)
else:
    print('Update aborted.')
