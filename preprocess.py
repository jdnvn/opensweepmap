import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import random
import pandas as pd
import numpy as np
import re

from sqlalchemy import create_engine, text

with open('/Users/joey/Documents/sweepmaps/geojsons/boston_sidewalks_geocoded.geojson', 'r') as f:
    output_sidewalks_geojson = json.load(f)

## PREPROCESS DATA ##
try:
    street_cleaning_df = pd.read_csv('data/street_cleaning_data_deduped.csv')
    sidewalk_df = pd.read_csv('data/sidewalk_data.csv')
except:
    ## NORMALIZE DATASETS ##
    street_cleaning_df = pd.read_csv('/Users/joey/Documents/sweepmaps/street_cleaning_good.csv')

    street_cleaning_df['suburb'] = street_cleaning_df['dist_name']
    street_cleaning_df.loc[street_cleaning_df['suburb'] == 'South Dorchester', 'suburb'] = 'Dorchester'
    street_cleaning_df.loc[street_cleaning_df['suburb'] == 'North Dorchester', 'suburb'] = 'Dorchester'
    street_cleaning_df.loc[street_cleaning_df['suburb'] == 'DCR', 'suburb'] = 'Dorchester'


    sidewalk_dict_list = [feature['properties'] for feature in output_sidewalks_geojson["features"]]
    sidewalk_df = pd.DataFrame(sidewalk_dict_list)
    sidewalk_df['suburb'].unique()

    rows_with_nan_in_A = sidewalk_df[sidewalk_df['suburb'].isna()]
    sidewalk_df.dropna(subset=['suburb'])

    sidewalk_df = sidewalk_df[sidewalk_df['suburb'] != 'East Cambridge']
    sidewalk_df = sidewalk_df[sidewalk_df['suburb'] != 'North Quincy']
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Fenway / Kenmore', 'suburb'] = 'Fenway/Kenmore'
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Allston', 'suburb'] = 'Allston/Brighton'
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Brighton', 'suburb'] = 'Allston/Brighton'
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Downtown Boston', 'suburb'] = 'Downtown'
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Chestnut Hill', 'suburb'] = 'Allston/Brighton'
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Newton Corner', 'suburb'] = 'Allston/Brighton'
    sidewalk_df.loc[sidewalk_df['suburb'] == 'Mattapan', 'suburb'] = 'Dorchester'


    def normalize_street_name(name):
        if not isinstance(name, str):
            return name
        name = name.lower()
        name = name.replace('road', 'rd').replace('boulevard', 'blvd').replace('street', 'st').replace('avenue', 'ave').replace('court', 'ct').replace('circle', 'cr').replace('terrace', 'ter').replace('square', 'sq').replace('drive', 'dr').replace('parkway', 'pkwy').replace('place', 'pl').replace('lane', 'ln').replace('plaza', 'plz')
        name = ''.join(char for char in name if char.isalnum() or char.isspace())
        return name.strip()

    street_cleaning_df['normalized_st_name'] = street_cleaning_df['st_name'].apply(normalize_street_name)
    street_cleaning_df.loc[street_cleaning_df['main_id'] == 3692, 'normalized_st_name'] = 'rockvale cr'
    street_cleaning_df.loc[street_cleaning_df['main_id'] == 3693, 'normalized_st_name'] = 'rockvale cr'
    street_cleaning_df.loc[street_cleaning_df['main_id'] == 1665, 'normalized_st_name'] = 'mamelon cr'
    street_cleaning_df.loc[street_cleaning_df['main_id'] == 1666, 'normalized_st_name'] = 'mamelon cr'
    street_cleaning_df.loc[street_cleaning_df['main_id'] == 2662, 'normalized_st_name'] = 'raynor cr'
    street_cleaning_df.loc[street_cleaning_df['main_id'] == 2663, 'normalized_st_name'] = 'raynor cr'


    sidewalk_df['normalized_st_name'] = sidewalk_df['road'].apply(normalize_street_name)


    def even_or_odd(number):
        if pd.isna(number):
            return 'none'

        parts = re.split(r'[;,-]', number)
        first_num = parts[0]
        num_str = ''.join(re.findall(r'\d+', first_num))
        try:
            result = 'even' if int(num_str) % 2 == 0 else 'odd'
        except Exception as e:
            print(f"error processing number '{number}': {e}")
            result = 'unknown'
        return result

    sidewalk_df['side'] = sidewalk_df['house_number'].apply(even_or_odd)

    street_cleaning_df['side'] = street_cleaning_df['side'].str.lower()
    street_cleaning_df['side'] = street_cleaning_df['side'].fillna('none')


    # make boolean value columns with all boolean cols
    bool_columns = ['one_way', 'week_1', 'week_2', 'week_3', 'week_4', 'week_5', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'every_day', 'year_round', 'north_end_pilot']
    for bool_column in bool_columns:
        street_cleaning_df[f"{bool_column}_bool"] = street_cleaning_df[bool_column] == 't'

    # there are some mistake duplicates
    street_cleaning_df = street_cleaning_df.drop_duplicates(subset=['suburb', 'normalized_st_name', 'side', 'from', 'to', 'start_time', 'end_time',  *bool_columns])


    street_cleaning_df.to_csv('data/street_cleaning_data_deduped.csv', index=False)
    sidewalk_df.to_csv('data/sidewalk_data.csv', index=False)

# DETERMINE DUPLICATE SCHEDULES
# TODO: go back and manually reassign schedules to sidewalks with multiple schedules - label as "maybe"
duplicates_with_diff_schedules = street_cleaning_df[street_cleaning_df.duplicated(subset=['suburb', 'normalized_st_name', 'side'], keep=False)]
duplicates_grouped = duplicates_with_diff_schedules.groupby(['suburb', 'normalized_st_name', 'side']).agg({
    'main_id': lambda x: list(x)  # collect all schedule ids
}).reset_index()
duplicates_grouped = duplicates_grouped.rename(columns={'main_id': 'duplicate_ids'})

# drop duplicates for now
street_cleaning_df_unique = street_cleaning_df.drop_duplicates(subset=['suburb', 'normalized_st_name', 'side'], keep='first')

# add duplicate ids column to cleaning df
street_cleaning_df_unique = pd.merge(street_cleaning_df_unique, duplicates_grouped, 
                            on=['suburb', 'normalized_st_name', 'side'], 
                            how='left')


# join the datasets
merged_df = pd.merge(sidewalk_df,
                     street_cleaning_df_unique,
                     left_on=['suburb', 'normalized_st_name', 'side'],
                     right_on=['suburb', 'normalized_st_name', 'side'],
                     how='left')
for bool_column in bool_columns:
    merged_df[bool_column] = merged_df[f"{bool_column}_bool"]
merged_df['street_name'] = merged_df['road']

columns_to_keep = ['OBJECTID', 'TYPE', 'ShapeSTLength', 'main_id', 'street_name', 'suburb', 'side', 'start_time', 'end_time', 'from', 'to', 'miles', 'section', *bool_columns]

output_df = merged_df[columns_to_keep]

output_dict_list = output_df.to_dict(orient='records')

output_dict_map = {}
for item in output_dict_list:
    output_dict_map[item['OBJECTID']] = item


for feature in output_sidewalks_geojson['features']:
    try:
        feature['properties'] = output_dict_map[feature['properties']['OBJECTID']]
    except Exception as e:
        print(f"error on ID '{feature['properties']['OBJECTID']}': {e}")
        print(feature['properties'])


with open('/Users/joey/Documents/sweepmaps/boston_street_cleaning_2.geojson', 'w') as outfile:
    json.dump(output_sidewalks_geojson, outfile)



## DB INGESTION ##
user = 'joey'
password = 'sweep'
host = 'localhost'
port = '5432'
database = 'sweepmaps'
engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')

# SCHEDULES
street_cleaning_db_df = street_cleaning_df.copy()
street_cleaning_db_df['id'] = street_cleaning_df['main_id']
street_cleaning_db_df['street_name'] = street_cleaning_df['st_name']
street_cleaning_db_df['suburb_name'] = street_cleaning_df['suburb']
street_cleaning_db_df['from_street_name'] = street_cleaning_df['from']
street_cleaning_db_df['to_street_name'] = street_cleaning_df['to']
street_cleaning_db_df['has_duplicates'] = street_cleaning_df['duplicate_ids'].notna()
for bool_column in bool_columns:
    street_cleaning_db_df[bool_column] = street_cleaning_df[f"{bool_column}_bool"]


schedules_db_columns = ['id', 'street_name', 'suburb_name', 'side', 'start_time', 'end_time', 'from_street_name', 'to_street_name', 'has_duplicates', *bool_columns]

schedules_table_df = street_cleaning_db_df[schedules_db_columns]

# fix one-offs that don't have a suburb name
schedules_table_df.loc[schedules_table_df['id'] == 3263, 'suburb_name'] = 'South Boston'
schedules_table_df.loc[schedules_table_df['id'] == 3312, 'suburb_name'] = 'Dorchester'
schedules_table_df.loc[schedules_table_df['id'] == 3313, 'suburb_name'] = 'Dorchester'
schedules_table_df.loc[schedules_table_df['id'] == 3435, 'suburb_name'] = 'Charlestown'
schedules_table_df.loc[schedules_table_df['id'] == 3443, 'suburb_name'] = 'Charlestown'
schedules_table_df.loc[schedules_table_df['id'] == 3536, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3746, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3747, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3748, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3749, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3750, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3751, 'suburb_name'] = 'South End'
schedules_table_df.loc[schedules_table_df['id'] == 3754, 'suburb_name'] = 'South End'


# insert data into postgres
schedules_table_df.to_sql('schedules', engine, if_exists='append', index=False)


# SIDEWALKS
# use merged DF to preserve relationship with schedules
sidewalk_db_df = merged_df.copy()
sidewalk_db_df['schedule_id_raw'] = pd.to_numeric(sidewalk_db_df['main_id'], errors='coerce')
sidewalk_db_df['schedule_id'] = sidewalk_db_df['schedule_id_raw'].astype('Int64')

def set_status(row):
    if pd.isna(row['schedule_id']):
        return 'missing'
    elif isinstance(row['duplicate_ids'], (list, pd.Series)) and len(row['duplicate_ids']) > 0:
        return 'unresolved'
    else:
        return 'ok'

sidewalk_db_df['status'] = sidewalk_db_df.apply(set_status, axis=1)

geometry_dict = {}
for feature in output_sidewalks_geojson['features']:
    geometry_dict[feature['properties']['OBJECTID']] = json.dumps(feature['geometry'])


# execute bulk insert of sidewalks
rows_to_insert = []

for i, sub_df in sidewalk_db_df.iterrows():
    geojson_str = geometry_dict.get(sub_df['OBJECTID'], None)
    schedule_id = sub_df['schedule_id'] if pd.notna(sub_df['schedule_id']) else None

    rows_to_insert.append({
        'schedule_id': schedule_id,
        'geojson': geojson_str,
        'status': sub_df['status']
    })

insert_sql = text("""
    INSERT INTO sidewalks (schedule_id, geometry, status)
    VALUES (:schedule_id, (SELECT(ST_GeomFromGeoJSON(:geojson))), :status);
""")

with engine.connect() as connection:
    transaction = connection.begin()
    try:
        result = connection.execute(insert_sql, rows_to_insert)
        transaction.commit()
        print("Insert successful")
    except Exception as e:
        transaction.rollback()
        print("An error occurred:", e)

