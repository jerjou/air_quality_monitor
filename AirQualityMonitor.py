import os
import datetime
import serial
import aqi
import sqlite3
from sds011lib import SDS011QueryReader

def get_db_cursor():
  return sqlite3.connect('data.db')

class AirQualityMonitor():

  def __init__(self, read_interval):
    for i in range(9):
      if os.path.exists(f'/dev/ttyUSB{i}'):
        self.sensor = SDS011QueryReader(f'/dev/ttyUSB{i}')
        break
    else:
      raise RuntimeError('ttyUSB not found.')

    self.sensor.set_working_period(read_interval)

    # Check if it exists before connecting, so we can create the table
    if not os.path.exists('data.db'):
      sqlite3.connect('data.db').cursor().execute(
        '''CREATE TABLE airquality
           (created datetime default current_timestamp,
           pm2 int,
           pm10 int,
           aqi real)''')

  def _get_measurement(self):
    reading = self.sensor.query()
    the_aqi = aqi.to_aqi([
      (aqi.POLLUTANT_PM25, str(reading.pm25)),
      (aqi.POLLUTANT_PM10, str(reading.pm10))
      ])

    return {
      "timestamp": datetime.datetime.now(),
      "pm2.5": reading.pm25,
      "pm10": reading.pm10,
      "aqi": float(the_aqi),
    }

  def save_measurement(self):
    measurement = self._get_measurement()
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
