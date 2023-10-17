import os
from flask import Flask, jsonify, render_template, request, Response
from AirQualityMonitor import AirQualityMonitor
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time
from flask_cors import CORS, cross_origin
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

MINUTES_PER_SAMPLE = 1

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
aqm = AirQualityMonitor()

scheduler = BackgroundScheduler()
scheduler.add_job(func=aqm.save_measurement, trigger="interval", minutes=MINUTES_PER_SAMPLE)
scheduler.start()

def cleanup():
    scheduler.shutdown()


atexit.register(cleanup)

def pretty_timestamps(measurement):
    timestamps = [
        datetime.strptime(m['timestamp'], '%Y-%m-%d %H:%M:%S').replace(
          tzinfo=timezone.utc).astimezone(ZoneInfo("America/New_York"))
        for m in measurement]
    if timestamps:
        # Label the date for only the ones where the day changes, and the first hour
        # of each new day (Not just the first entry, because the graph may not end
        # up using that label for coarse grid lines)
        return [timestamps[0].strftime('%a %m/%d %H:%M')] + [
            dt.strftime('%H:%M' if dt.hour else '%a %m/%d %H:%M')
            for dt in timestamps[1:]]
    else:
        return []

def reconfigure_data(measurement):
    """Reconfigures data for chart.js"""
    measurement.reverse()
    return {
        'labels': pretty_timestamps(measurement),
        'aqi': {
            'label': 'aqi',
            'data': [x['aqi'] for x in measurement],
            'backgroundColor': '#181d27',
            'borderColor': '#181d27',
            'borderWidth': 3,
        },
        'pm10': {
            'label': 'pm10',
            'data': [x['pm10'] for x in measurement],
            'backgroundColor': '#cc0000',
            'borderColor': '#cc0000',
            'borderWidth': 3,
        },
        'pm2': {
            'label': 'pm2.5',
            'data': [x['pm2.5'] for x in measurement],
            'backgroundColor': '#42C0FB',
            'borderColor': '#42C0FB',
            'borderWidth': 3,
        },
    }

@app.route('/')
def index():
    """Index page for the application"""
    hours = int(request.args.get('hours', 24))
    return render_template(
        'index.html',
        historical=reconfigure_data(aqm.get_latest(
          hours * 60 / MINUTES_PER_SAMPLE)),
        minsPerSample=MINUTES_PER_SAMPLE,
        )


@app.route('/api/')
@cross_origin()
def api():
    """Returns historical data from the sensor"""
    hours = int(request.args.get('hours', 24))
    return jsonify(reconfigure_data(aqm.get_latest(
      hours * 60 / MINUTES_PER_SAMPLE)))


def stream(hours):
    get = lambda: aqm.get_latest(hours * 60 / MINUTES_PER_SAMPLE)
    old_data = get()
    while True:
        new_data = get()
        if new_data != old_data:
            old_data = new_data
            yield 'event: data\ndata: {}\n\n'.format(
                    json.dumps(reconfigure_data(new_data)))
            time.sleep(MINUTES_PER_SAMPLE * 60)
        else:
            time.sleep(10)

@app.route('/api/listen')
def api_listen():
    hours = int(request.args.get('hours', 24))
    return Response(stream(hours), mimetype='text/event-stream')

if __name__ == "__main__":
    #app.run(debug=True, use_reloader=False, host='0.0.0.0',
    #    port=int(os.environ.get('PORT', '8000')))
    import bjoern
    bjoern.run(app, "0.0.0.0", int(os.environ.get('PORT', '8000')))
