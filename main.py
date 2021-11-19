#!/usr/bin/env python3

import json
import sqlite3
import os
import contextlib

import fastapi

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

def get_all_stats(start_datetime, end_datetime):
    return db.select(
        '''
        select
            count(*) as measurement_count,
            sum(m.consumption),
            avg(m.temp),
            sum(m.flow_time),
            sum(m.power_consumption)
        from measurements m
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where m.timestamp >= ?
            and m.timestamp < ?
        ''',
        [
            start_datetime,
            end_datetime
        ]
    )[0]


def get_apartment_stats(apartment_id, start_datetime, end_datetime):
    return db.select(
        '''
        select
            count(*) as measurement_count,
            sum(m.consumption),
            avg(m.temp),
            sum(m.flow_time),
            sum(m.power_consumption)
        from measurements m
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where a.id = ?
            and m.timestamp >= ?
            and m.timestamp < ?
        ''',
        [
            apartment_id,
            start_datetime,
            end_datetime
        ]
    )[0]

def get_apartment_device_stats(apartment_id, start_datetime, end_datetime):
    return db.select(
        '''
        select
            d.name as device_name,
            count(*) as measurement_count,
            sum(m.consumption),
            avg(m.temp),
            sum(m.flow_time),
            sum(m.power_consumption)
        from measurements m
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where a.id = ?
            and m.timestamp >= ?
            and m.timestamp < ?
        group by d.name
        ''',
        [
            apartment_id,
            start_datetime,
            end_datetime
        ]
    )

db = populate_db()
app = fastapi.FastAPI()

@app.get('/apartment_stats/{apartment_id}')
async def query_apartment_stats(apartment_id, start, end):
    return get_apartment_stats(apartment_id, start, end)

@app.get('/all_stats')
async def query_all_stats(start, end):
    return get_all_stats(start, end)

@app.get('/apartment_device_stats/{apartment_id}')
async def query_apartment_device_stats(apartment_id, start, end):
    return get_apartment_device_stats(apartment_id, start, end)
