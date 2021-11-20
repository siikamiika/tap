#!/usr/bin/env python3

import json
import sqlite3
import os
import contextlib
import functools

import fastapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

class DB:
    def __init__(self, db_path):
        self._db_path = db_path
        self._con = self._get_db_connection()
        self._con.row_factory = sqlite3.Row
        self._cur = self._con.cursor()
        self._ensure_tables()

    def select(self, sql, params=[]):
        self._execute(sql, params)
        return self._cur.fetchall()

    def insert(self, sql, params=[]):
        self._execute(sql, params)
        return self._cur.lastrowid

    def _execute(self, sql, params=[]):
        self._cur.execute(sql, params)

    def commit(self):
        self._con.commit()

    def _get_db_connection(self):
        path = self._db_path
        if not os.path.isfile(path):
            fd = os.open(path, os.O_CREAT, mode=0o600)
            os.close(fd)
        return sqlite3.connect(path, check_same_thread=False)

    def _ensure_tables(self):
        self._execute('''
            CREATE TABLE IF NOT EXISTS apartments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                people INTEGER NOT NULL
            )
        ''')
        self._execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apartment_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY(apartment_id) REFERENCES apartments(id)
            )
        ''')
        self._execute('CREATE INDEX IF NOT EXISTS apartment_id_idx ON devices (apartment_id)')
        self._execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                consumption REAL NOT NULL,
                temp REAL NOT NULL,
                flow_time REAL NOT NULL,
                power_consumption REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(device_id) REFERENCES devices(id)
            )
        ''')
        self._execute('CREATE INDEX IF NOT EXISTS device_id_idx ON measurements (device_id)')
        self.commit()

def populate_db():
    with contextlib.suppress(FileNotFoundError):
        os.remove('app.db')

    with open('db.json') as f:
        data = json.load(f)

    db = DB('app.db')
    for apartment in data['houses'][0]['apartments']:
        apartment_id = db.insert(
            'INSERT INTO apartments (people) VALUES (?)',
            [
                int(apartment['people']),
            ]
        )
        for key, device in apartment.items():
            if key == 'people':
                continue
            device_id = db.insert(
                'INSERT INTO devices (apartment_id, name) VALUES (?, ?)',
                [
                    int(apartment_id),
                    key,
                ]
            )
            for measurement in device['measurements']:
                db.insert(
                    '''
                    INSERT INTO measurements (
                        device_id,
                        consumption,
                        temp,
                        flow_time,
                        power_consumption,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    [
                        int(device_id),
                        float(measurement['Consumption']),
                        float(measurement['Temp']),
                        float(measurement['FlowTime']),
                        float(measurement['Power_Consumption']),
                        measurement['TimeStamp'].replace('T', ' '),
                    ]
                )
    db.commit()
    return db

@functools.lru_cache(maxsize=20)
def get_apartment_stats(apartment_id, start_datetime, end_datetime):
    return db.select(
        '''
        select
            count(*) as measurement_count,
            avg(a.people) as _average_people,
            sum(m.consumption) / avg(a.people) as total_consumption,
            avg(m.temp) as average_temperature,
            sum(m.flow_time) / avg(a.people) as total_flow_time,
            sum(m.power_consumption) / avg(a.people) as total_power_consumption
        from measurements m
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where (? or a.id = ?)
            and m.timestamp >= ?
            and m.timestamp < ?
        ''',
        [
            apartment_id == 'all',
            apartment_id,
            start_datetime,
            end_datetime
        ]
    )[0]

@functools.lru_cache(maxsize=20)
def get_apartment_device_stats(apartment_id, start_datetime, end_datetime):
    return {
        row['device_name']: row
        for row in db.select(
            '''
            select
                case
                    when d.name in ('Hydractiva_shower', 'Kitchen_optima_faucet', 'Optima_faucet') then 'manual'
                    when d.name in ('Washing_machine', 'Dishwasher') then 'automatic'
                    else null
                end as device_name,
                count(*) as measurement_count,
                avg(a.people) as _average_people,
                sum(m.consumption) / avg(a.people) as total_consumption,
                avg(m.temp) as average_temperature,
                sum(m.flow_time) / avg(a.people) as total_flow_time,
                sum(m.power_consumption) / avg(a.people) as total_power_consumption
            from measurements m
            join devices d on m.device_id = d.id
            join apartments a on d.apartment_id = a.id
            where (? or a.id = ?)
                and m.timestamp >= ?
                and m.timestamp < ?
            group by device_name
            ''',
            [
                apartment_id == 'all',
                apartment_id,
                start_datetime,
                end_datetime
            ]
        )
    }

@functools.lru_cache(maxsize=20)
def get_ordered_apartment_device_consumption(device_name, start_datetime, end_datetime, order):
    if order not in ['asc', 'desc']:
        raise Exception('Invalid order')
    return db.select(
        f'''
        select
            a.id as apartment_id,
            case
                when d.name in ('Hydractiva_shower', 'Kitchen_optima_faucet', 'Optima_faucet') then 'manual'
                when d.name in ('Washing_machine', 'Dishwasher') then 'automatic'
                else null
            end as _device_name,
            avg(a.people) as _average_people,
            count(*) as measurement_count,
            sum(m.consumption) / avg(a.people) as total_consumption,
            avg(m.temp) as average_temperature,
            sum(m.flow_time) / avg(a.people) as total_flow_time,
            sum(m.power_consumption) / avg(a.people) as total_power_consumption
        from measurements m
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where (? or _device_name = ?)
            and m.timestamp >= ?
            and m.timestamp < ?
        group by a.id
        order by total_consumption {order}
        limit 1
        ''',
        [
            device_name == 'all',
            device_name,
            start_datetime,
            end_datetime
        ]
    )[0]

def get_device_specific_consumption(start_datetime, end_datetime):
    rows = db.select(
        f'''
        with time_interval as (
            select ((julianday(?) - julianday(?)) * 86400.0) as value
        )
        select
            a.id as apartment_id,
            d.name as device_name,
            count(*) as measurement_count,
            sum(m.consumption) as total_consumption,
            avg(m.temp) as average_temperature,
            sum(m.flow_time) as total_flow_time,
            sum(min(m.flow_time, time_interval.value)) / time_interval.value as flow_percentage,
            sum(m.power_consumption) as total_power_consumption
        from measurements m, time_interval
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where m.timestamp >= ?
            and m.timestamp < ?
        group by a.id, d.id
        ''',
        [
            end_datetime,
            start_datetime,
            start_datetime,
            end_datetime,
        ]
    )
    data = {}
    for row in rows:
        if row['apartment_id'] not in data:
            data[row['apartment_id']] = {}
        data[row['apartment_id']][row['device_name']] = row
    return data

db = populate_db()
app = fastapi.FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/')
async def main():
    return FileResponse('static/index.html')

@app.get('/details')
async def main():
    return FileResponse('static/details.html')

@app.get('/favicon.ico')
async def favicon():
    return FileResponse('static/favicon.ico')

# combined stats for all devices

# everything in one request
@app.get('/stats/{apartment_id}')
async def query_stats(apartment_id, start, end):
    device_names = ['automatic', 'manual']
    return {
        'apartment_stats': get_apartment_stats(apartment_id, start, end),
        'all_stats': get_apartment_stats('all', start, end),
        'apartment_device_stats': get_apartment_device_stats(apartment_id, start, end),
        'all_device_stats': get_apartment_device_stats('all', start, end),
        'smallest_apartment_device_consumption': {
            device_name: get_ordered_apartment_device_consumption(device_name, start, end, 'asc')
            for device_name in device_names
        },
        'largest_apartment_device_consumption': {
            device_name: get_ordered_apartment_device_consumption(device_name, start, end, 'desc')
            for device_name in device_names
        },
        'smallest_apartment_total_consumption':  get_ordered_apartment_device_consumption('all', start, end, 'asc'),
        'largest_apartment_total_consumption': get_ordered_apartment_device_consumption('all', start, end, 'desc'),
    }

@app.get('/apartment_stats/{apartment_id}')
async def query_apartment_stats(apartment_id, start, end):
    return get_apartment_stats(apartment_id, start, end)

@app.get('/all_stats')
async def query_all_stats(start, end):
    return get_apartment_stats('all', start, end)

# stats per device

@app.get('/apartment_device_stats/{apartment_id}')
async def query_apartment_device_stats(apartment_id, start, end):
    return get_apartment_device_stats(apartment_id, start, end)

@app.get('/all_device_stats')
async def query_all_device_stats(start, end):
    return get_apartment_device_stats('all', start, end)

# min/max consumption for a specific device

@app.get('/smallest_apartment_device_consumption')
async def query_smallest_apartment_device_consumption(device_name, start, end):
    return get_ordered_apartment_device_consumption(device_name, start, end, 'asc')

@app.get('/largest_apartment_device_consumption')
async def query_largest_apartment_device_consumption(device_name, start, end):
    return get_ordered_apartment_device_consumption(device_name, start, end, 'desc')

# min/max consumption for all devices

@app.get('/smallest_apartment_total_consumption')
async def query_smallest_apartment_total_consumption(start, end):
    return get_ordered_apartment_device_consumption('all', start, end, 'asc')

@app.get('/largest_apartment_total_consumption')
async def query_largest_apartment_total_consumption(start, end):
    return get_ordered_apartment_device_consumption('all', start, end, 'desc')

# plumber

@app.get('/device_specific_consumption')
async def query_device_specific_consumption(start, end):
    return get_device_specific_consumption(start, end)
