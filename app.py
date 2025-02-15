import os
from flask import Flask, jsonify, render_template, request, Response
from AirQualityMonitor import AirQualityMonitor
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time
from datetime import datetime, timedelta
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

MINUTES_PER_SAMPLE = 10
LOCALTZ = ZoneInfo('America/New_York')

app = Flask(__name__)
aqm = AirQualityMonitor(MINUTES_PER_SAMPLE)

scheduler = BackgroundScheduler()
scheduler.add_job(
    next_run_time=datetime.now() + timedelta(seconds=10),
    func=aqm.save_measurement,
    trigger="interval",
    minutes=MINUTES_PER_SAMPLE)
scheduler.start()

def cleanup():
    scheduler.shutdown()
    aqm.sensor.sleep()


atexit.register(cleanup)

def pretty_timestamps(measurement):
    timestamps = [
        datetime.strptime(m['timestamp'], '%Y-%m-%d %H:%M:%S').replace(
          tzinfo=timezone.utc).astimezone(LOCALTZ)
        for m in measurement]
    if timestamps:
        return [dt.timestamp() for dt in timestamps]
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

def _get_content(args):
  if 'from' in args:
    parse = lambda t: datetime.strptime(
        t, '%Y%m%d' if len(t) == 8 else '%Y%m%d%H%M').replace(tzinfo=LOCALTZ)

    from_ = parse(args['from'])
    to = (parse(args['to']) if 'to' in args
          else from_ + timedelta(hours=24))
    return aqm.get_range(from_, to)

  else:
    return aqm.get_latest(int(args.get('hours', 24)))

@app.route('/')
def index():
  """Index page for the application"""
  return render_template(
      'index.html',
      historical=reconfigure_data(_get_content(request.args)),
      minsPerSample=MINUTES_PER_SAMPLE,
      )

@app.route('/api/')
def api():
    """Returns historical data from the sensor"""
    return jsonify(reconfigure_data(_get_content(request.args)))


def stream(args):
    old_data = None
    while True:
        new_data = _get_content(args)
        if new_data != old_data:
            old_data = new_data
            yield 'event: data\ndata: {}\n\n'.format(
                    json.dumps(reconfigure_data(new_data)))
            time.sleep(MINUTES_PER_SAMPLE * 60 * .5)
        else:
            time.sleep(10)

@app.route('/api/listen')
def api_listen():
    # Apparently bjoern is single-threaded, so maybe server-sent events isn't
    # the best idea...
    return Response(stream(request.args), mimetype='text/event-stream')

if __name__ == "__main__":
    #app.run(debug=True, use_reloader=False, host='0.0.0.0',
    #    port=int(os.environ.get('PORT', '8000')))
    import bjoern
    bjoern.run(app, "0.0.0.0", int(os.environ.get('PORT', '8000')))
