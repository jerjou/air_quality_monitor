import os
import datetime
import serial
import aqi
import sqlite3


def get_db_cursor():
    return sqlite3.connect('data.db')

class AirQualityMonitor():

    def __init__(self):
        self.ser = serial.Serial('/dev/ttyUSB0')
        # Check if it exists before connecting, so we can create the table
        if not os.path.exists('data.db'):
            sqlite3.connect('data.db').cursor().execute(
                '''CREATE TABLE airquality
                   (created datetime default current_timestamp,
                   pm2 int,
                   pm10 int,
                   aqi real)''')

    def get_measurement(self):
        data = []
        for index in range(0,10):
            datum = self.ser.read()
            data.append(datum)
        pmtwo = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
        pmten = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10
        myaqi = aqi.to_aqi([(aqi.POLLUTANT_PM25, str(pmtwo)),
                            (aqi.POLLUTANT_PM10, str(pmten))])
        self.aqi = float(myaqi)

        return {
            "timestamp": datetime.datetime.now(),
            "pm2.5": pmtwo,
            "pm10": pmten,
            "aqi": self.aqi,
        }

    def save_measurement(self):
        measurement = self.get_measurement()
        with get_db_cursor() as conn:
            conn.execute(
                'insert into airquality (pm2, pm10, aqi) values (?, ?, ?)',
                (measurement['pm2.5'], measurement['pm10'], measurement['aqi']))

    def get_latest(self, n=100):
        """Returns the last n measurements in the list"""
        return [{
            'timestamp': created,
            'pm2.5': pm2,
            'pm10': pm10,
            'aqi': aqi,
        } for created, pm2, pm10, aqi in get_db_cursor().execute(
            'select created, pm2, pm10, aqi from airquality '
            'order by created desc limit ?',
            (n,)).fetchall()]
