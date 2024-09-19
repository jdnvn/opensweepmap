import pandas as pd
import json

with open('geojsons/boston_streets.geojson', 'r') as f:
    streets_geojson = json.load(f)

streets_properties = [street_feature['properties'] for street_feature in streets_geojson['features']]
streets_df = pd.DataFrame(streets_properties)
streets_df['st_type'] = streets_df['ST_TYPE'].str.lower()

street_cleaning_df = pd.read_csv('data/street_cleaning_good.csv')
street_cleaning_df['st_type'] = street_cleaning_df['st_name'].apply(lambda x: x.split()[-1].lower())
street_cleaning_df['from_st_type'] = street_cleaning_df['from'].apply(lambda x: str(x).split()[-1].lower())
street_cleaning_df['to_st_type'] = street_cleaning_df['to'].apply(lambda x: str(x).split()[-1].lower())

street_cleaning_df.loc[street_cleaning_df['st_type'] == 'cr', 'st_type'] = 'cres'
street_cleaning_df.loc[street_cleaning_df['st_type'] == "st'", 'st_type'] = 'st'

street_cleaning_df.loc[street_cleaning_df['from_st_type'] == "street", 'from_st_type'] = 'st'
street_cleaning_df.loc[street_cleaning_df['from_st_type'] == "av", 'from_st_type'] = 'ave'
street_cleaning_df.loc[street_cleaning_df['from_st_type'] == "avenue", 'from_st_type'] = 'ave'
street_cleaning_df.loc[street_cleaning_df['from_st_type'] == "place", 'from_st_type'] = 'pl'
street_cleaning_df.loc[street_cleaning_df['from_st_type'] == "square", 'from_st_type'] = 'sq'
street_cleaning_df.loc[street_cleaning_df['from_st_type'] == "road", 'from_st_type'] = 'rd'
street_cleaning_df.loc[street_cleaning_df['from'] == "Dead End", 'from_st_type'] = 'dead'

street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "street", 'to_st_type'] = 'st'
street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "av", 'to_st_type'] = 'ave'
street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "avenue", 'to_st_type'] = 'ave'
street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "place", 'to_st_type'] = 'pl'
street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "square", 'to_st_type'] = 'sq'
street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "road", 'to_st_type'] = 'rd'
street_cleaning_df.loc[street_cleaning_df['to_st_type'] == "wharf", 'to_st_type'] = 'whrf'

street_cleaning_df.loc[street_cleaning_df['to'] == "Dead End", 'to_st_type'] = 'dead'




street_cleaning_df['st_name'] = street_cleaning_df['st_name'].apply(lambda x: ' '.join(x.split()[:-1]).lower())
street_cleaning_df['from_st_name'] = street_cleaning_df['from'].apply(lambda x: ' '.join(str(x).split()[:-1]).lower())
street_cleaning_df['to_st_name'] = street_cleaning_df['to'].apply(lambda x: ' '.join(str(x).split()[:-1]).lower())

streets_df['st_name'] = streets_df['ST_NAME'].str.lower()

street_cleaning_df['dist_name'].unique()
streets_df['dist_name'] = streets_df['NBHD_L']
streets_df['dist_name'].unique()

streets_df.loc[streets_df['dist_name'] == "Allston-Brighton", 'dist_name'] = 'Allston/Brighton'
streets_df.loc[streets_df['dist_name'] == "Dorcheseter", 'dist_name'] = 'Dorchester'

street_cleaning_df.loc[street_cleaning_df['dist_name'] == 'South Dorchester', 'dist_name'] = 'Dorchester'
street_cleaning_df.loc[street_cleaning_df['dist_name'] == 'North Dorchester', 'dist_name'] = 'Dorchester'
street_cleaning_df.loc[street_cleaning_df['dist_name'] == 'DCR', 'dist_name'] = 'Dorchester'
street_cleaning_df.loc[street_cleaning_df['dist_name'].isin(['Back Bay','Beacon Hill','Chinatown','Downtown','Fenway/Kenmore','Mission Hill','North End','South End', 'West End']), 'dist_name'] = 'Boston'

streets_uniq_df = streets_df.drop_duplicates(subset=['dist_name', 'st_name', 'st_type'], keep='first')
streets_uniq_df = streets_uniq_df.rename(columns={'STREET_ID': 'street_id'})

schedule_with_street = pd.merge(street_cleaning_df, streets_uniq_df, 
                            left_on=['dist_name', 'st_type', 'st_name'],
                            right_on=['dist_name', 'st_type', 'st_name'], 
                            how='left')

schedule_with_from_street = pd.merge(schedule_with_street, streets_uniq_df, 
                            left_on=['dist_name', 'from_st_type', 'from_st_name'],
                            right_on=['dist_name', 'st_type', 'st_name'], 
                            how='left')
schedule_with_from_street = schedule_with_from_street.rename(columns={'street_id_y': 'from_street_id'})

schedule_with_to_street = pd.merge(schedule_with_from_street, streets_uniq_df, 
                            left_on=['dist_name', 'to_st_type', 'to_st_name'],
                            right_on=['dist_name', 'st_type', 'st_name'], 
                            how='left')
schedule_with_streets = schedule_with_to_street.rename(columns={'street_id_x': 'to_street_id'})

schedules_with_all_streets = schedule_with_streets.dropna(subset=['street_id', 'from_street_id', 'to_street_id'])
schedules_with_all_streets[['street_id', 'from_street_id', 'to_street_id']] = schedules_with_all_streets[['street_id', 'from_street_id', 'to_street_id']].astype(int)


unique_street_ids = pd.unique(schedules_with_all_streets[['street_id', 'from_street_id', 'to_street_id']].values.ravel())

## Ingest streets and add foreign keys to schedules
streets_df['street_id'] = streets_df['STREET_ID']
streets_df['name'] = streets_df['ST_NAME']
streets_df['type'] = streets_df['ST_TYPE']
streets_df['suburb'] = streets_df['dist_name']
streets_df['city'] = streets_df['MUN_L']
streets_df['state'] = streets_df['STATE00_L']

streets_df_db = streets_df[['street_id', 'name', 'type', 'suburb', 'city', 'state', '']]


records_to_insert = []
for feature in streets_geojson['features']:
    street_id = feature['properties']['STREET_ID']
    if street_id in unique_street_ids:
        street_data = streets_df_db[streets_df_db['street_id'] == street_id].iloc[0]
        records_to_insert.append({
            "street_id": feature['properties']['STREET_ID'],
            "name": street_data['name'],
            "type": street_data['type'],
            "suburb": street_data['suburb'],
            "city": street_data['city'],
            "state": street_data['state'],
            "geojson": json.dumps(feature['geometry'])
        })

insert_sql = text("""
    INSERT INTO street_segments (street_id, name, type, suburb, city, state, geometry)
    VALUES (:street_id, :name, :type, :suburb, :city, :state, (SELECT(ST_GeomFromGeoJSON(:geojson))));
""")

with engine.connect() as connection:
    transaction = connection.begin()
    try:
        result = connection.execute(insert_sql, records_to_insert)
        transaction.commit()
        print("Insert successful")
    except Exception as e:
        transaction.rollback()
        print("An error occurred:", e)

# EXECUTE SQL #

# CREATE TABLE street_segments (
#     id SERIAL PRIMARY KEY,
#     street_id INTEGER,
#     name VARCHAR(255) NOT NULL,
#     type VARCHAR(255) NOT NULL,
#     suburb VARCHAR(255) NOT NULL,
#     city VARCHAR(255) NOT NULL,
#     state VARCHAR(255) NOT NULL,
#     geometry Geometry(LINESTRING)
# );

# CREATE TABLE streets AS
# SELECT
#     street_id AS id,
#     name,
#     type,
#     suburb,
#     city,
#     state,
#     ST_Union(geometry) AS geometry
# FROM
#     street_segments
# GROUP BY
#     street_id, name, type, suburb, city, state;


from sqlalchemy import create_engine, text, MetaData, Table, update, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from models import Sidewalk, Schedule
from datetime import datetime, timedelta
from geoalchemy2.functions import ST_AsGeoJSON


DATABASE_URL = f'postgresql://joey:sweep@localhost:5432/sweepmaps'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# now update schedule records
for i, sub_df in schedules_with_all_streets.iterrows():
    print(f"updating schedule {sub_df.main_id} - {sub_df.street_id}, {sub_df.from_street_id}, {sub_df.to_street_id}")
    with Session() as session:
        stmt = (
            update(Schedule).
            where(Schedule.id == sub_df.main_id).
            values(street_id=sub_df.street_id, from_street_id=sub_df.from_street_id, to_street_id=sub_df.to_street_id)
        )

        session.execute(stmt)
        session.commit()



query = text("""
WITH intersection_points AS (
        SELECT
            s.id AS schedule_id,
            st_full.geometry AS full_street_geometry,
            st_main.geometry AS st_main_segment,
            ST_ClosestPoint(st_full.geometry, ST_Intersection(st_main.geometry, st_from.geometry)) AS from_intersection,
            ST_ClosestPoint(st_full.geometry, ST_Intersection(st_main.geometry, st_to.geometry)) AS to_intersection
        FROM
            schedules s
        JOIN
            street_segments st_from ON s.from_street_id = st_from.street_id  -- Cross street for "from"
        JOIN
            street_segments st_to ON s.to_street_id = st_to.street_id        -- Cross street for "to"
        JOIN
            street_segments st_main ON s.street_id = st_main.street_id       -- Main street geometry
        JOIN
            streets st_full ON s.street_id = st_full.id
        WHERE
            ST_Intersects(st_main.geometry, st_from.geometry)
            AND ST_Intersects(st_main.geometry, st_to.geometry)
            AND ST_GeometryType(ST_Intersection(st_main.geometry, st_from.geometry)) = 'ST_Point'
            AND ST_GeometryType(ST_Intersection(st_main.geometry, st_to.geometry)) = 'ST_Point'
            AND ST_GeometryType(st_full.geometry) = 'ST_LineString'
        GROUP BY schedule_id, st_main.geometry, st_from.geometry, st_to.geometry, st_full.geometry
    )

    SELECT
        schedule_id,
        ST_AsGeoJSON(
            ST_LineSubstring(
                full_street_geometry,
                LEAST(ST_LineLocatePoint(full_street_geometry, from_intersection), ST_LineLocatePoint(full_street_geometry, to_intersection)),
                GREATEST(ST_LineLocatePoint(full_street_geometry, from_intersection), ST_LineLocatePoint(full_street_geometry, to_intersection))
            )
        ) AS street_segment_geojson
    FROM
        intersection_points
""")

with engine.connect() as connection:
    result = connection.execute(query)
    schedule_street_segments = result.fetchall()

feature_collection = { "type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}}
features = []
for segment in schedule_street_segments:
    metadata = schedules_with_all_streets[schedules_with_all_streets['main_id']==segment[0]].iloc[0].to_dict()
    feature = {"type": "Feature", "geometry": json.loads(segment[1]), **metadata}
    features.append(feature)

feature_collection["features"] = features

with open('geojsons/street_cleaning_schedule_segments.geojson', 'w') as f:
    json.dump(feature_collection, f)


# Conclusion - street segments do not come out well, and there are very few
# better off annotating by hand for now