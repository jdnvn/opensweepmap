from flask import Flask, jsonify, request, render_template
from sqlalchemy import create_engine, text, MetaData, Table, update, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from models import Sidewalk, Schedule
from datetime import datetime, timedelta
from geoalchemy2.functions import ST_AsGeoJSON

app = Flask(__name__)

user = 'joey'
password = 'sweep'
host = 'localhost'
port = '5432'
database = 'sweepmaps'

# Replace with your actual database URL
DATABASE_URL = f'postgresql://{user}:{password}@{host}:{port}/{database}'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


@app.route('/')
def map_view():
    return render_template('map.html')


def get_next_sweeping_date(schedule):
    # Define days of the week mapping
    days_of_week = {
        'sunday': 6,
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5
    }

    today = datetime.now().weekday()
    days = {
        'monday': schedule.get('monday', False),
        'tuesday': schedule.get('tuesday', False),
        'wednesday': schedule.get('wednesday', False),
        'thursday': schedule.get('thursday', False),
        'friday': schedule.get('friday', False),
        'saturday': schedule.get('saturday', False),
        'sunday': schedule.get('sunday', False)
    }

    # Check if sweeping is every day
    if schedule.get('every_day', False):
        next_sweep_date = datetime.now() + timedelta(days=1)
        return next_sweep_date.strftime('%Y-%m-%d')

    # Find the next sweeping day
    for i in range(1, 8):  # Check up to a week ahead
        next_date = datetime.now() + timedelta(days=i)
        next_weekday = next_date.weekday()
        if days.get(next_weekday, False):
            return next_date.strftime('%Y-%m-%d')

    return None


def get_sidewalks_data(ids=[], as_json=True, session=None):
    with Session() as session:
        sidewalks_query = session.query(
            Sidewalk.id,
            Sidewalk.schedule_id,
            Sidewalk.status,
            func.ST_AsGeoJSON(Sidewalk.geometry).label('geojson'),
            Schedule.street_name,
            Schedule.suburb_name,
            Schedule.side,
            Schedule.start_time,
            Schedule.end_time,
            Schedule.from_street_name,
            Schedule.to_street_name,
            Schedule.has_duplicates,
            Schedule.one_way,
            Schedule.week_1,
            Schedule.week_2,
            Schedule.week_3,
            Schedule.week_4,
            Schedule.week_5,
            Schedule.sunday,
            Schedule.monday,
            Schedule.tuesday,
            Schedule.wednesday,
            Schedule.thursday,
            Schedule.friday,
            Schedule.saturday,
            Schedule.every_day,
            Schedule.year_round,
            Schedule.north_end_pilot
        ).outerjoin(Schedule, Sidewalk.schedule_id == Schedule.id)

        if ids:
            sidewalks_query = sidewalks_query.filter(Sidewalk.id.in_(ids))

        sidewalks_data = sidewalks_query.all()
        if as_json:
            sidewalks_data = [row._asdict() for row in sidewalks_data]

    return sidewalks_data


@app.route('/sidewalks', methods=['GET'])
def get_sidewalks():
    try:
        sidewalks = get_sidewalks_data()
        sidewalks = [{**sidewalk, "next_sweep": get_next_sweeping_date(sidewalk)} for sidewalk in sidewalks]

        return jsonify({"data": sidewalks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/sidewalks/<id>', methods=['PUT'])
def put_sidewalk(id):
    sidewalks = get_sidewalks_data(ids=[id])
    if not sidewalks:
        return jsonify({'message': 'not found'}), 404

    sidewalk = sidewalks[0]

    try:
        content = request.get_json()
        print("incoming PUT request for sidewalk id: ", id)
        print(content)
        schedule_id = content["schedule_id"]
        status = content["status"]
    except Exception as e:
        print("ERROR: {e}")
        return jsonify({'error': str(e), 'message': 'Invalid request body'}), 422

    if sidewalk['schedule_id'] != int(schedule_id):
        status = 'ok'

    try:
        with Session() as session:
            stmt = (
                update(Sidewalk).
                where(Sidewalk.id == id).
                values(schedule_id=schedule_id, status=status)
            )

            session.execute(stmt)
            session.commit()

        updated_sidewalk = get_sidewalks_data(ids=[id])[0]
    except Exception as e:
        print("ERROR: {e}")
        return jsonify({'error': str(e), 'message': 'Something went wrong'}), 500

    print(f"updated sidewalk: {updated_sidewalk}")

    return jsonify(updated_sidewalk)



if __name__ == '__main__':
    app.run(debug=True)
