# Raspberry Pi Air Quality Monitor
A simple air quality monitoring service for the Raspberry Pi.

## Installation
Clone the repository and run the following:
```bash
# Create a fresh virtualenv
python3 -m venv --system-site-packages venv venv
source venv/bin/activate
# Install the dependencies
pip install -r requirements.txt
```

## Running
```bash
python3 app.py
```

## Useful references

* [SDS011 datasheet](https://cdn-reichelt.de/documents/datenblatt/X200/SDS011-DATASHEET.pdf)
* [Air Quality Index meaning](https://www.airnow.gov/aqi/aqi-basics/)
