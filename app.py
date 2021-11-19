#!/usr/bin/env python3

import json
import sqlite3
import os
import contextlib

class DB:
    def __init__(self, db_path):
        self._db_path = db_path
        self._con = self._get_db_connection()
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

    def _get_db_connection(self) -> sqlite3.Connection:
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

def get_apartment_measurements(apartment_id):
    db = DB('app.db')
    print(db.select(
        '''
        select count(*)
        from measurements m
        join devices d on m.device_id = d.id
        join apartments a on d.apartment_id = a.id
        where a.id = ?;
        ''',
        [apartment_id]
    ))

def main():
    populate_db()
    get_apartment_measurements(5)

if __name__ == '__main__':
    main()
