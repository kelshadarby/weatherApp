from datetime import datetime

import openmeteo_requests
import geocoder
import json
import requests
import pandas as pd
from django.http import HttpResponse
from django.template import loader
import requests_cache
from retry_requests import retry

from meteo.models import Worldcities


def temp_somewhere(request):
    random_item = Worldcities.objects.all().order_by('?').first()
    city = random_item.city
    location = [random_item.lat, random_item.lng]
    temp = get_temp(location)
    template = loader.get_template('index.html')
    context = {
        'city': city,
        'temp': temp
    }
    return HttpResponse(template.render(context, request))


def temp_here(request):
    location = geocoder.ip('me').latlng
    temp = get_temp(location)
    template = loader.get_template('index.html')
    context = {
        'city': 'your location',
        'temp': temp
    }
    return HttpResponse(template.render(context, request))


def get_temp(location):
    endpoint = "https://api.open-meteo.com/v1/forecast"
    api_request = f"{endpoint}?latitude={location[0]}&longitude={location[1]}&hourly=temperature_2m&temperature_unit=fahrenheit"
    current_hour = datetime.now().hour
    json = requests.get(api_request).json()
    meteo_data = json
    temp = meteo_data['hourly']['temperature_2m'][current_hour]
    return temp

def get_weather(request):
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 52.52,
        "longitude": 13.41,
        "daily": ["showers_sum", "weather_code", "snowfall_sum", "rain_sum", "precipitation_probability_max",
                  "wind_speed_10m_max", "temperature_2m_max", "temperature_2m_min", "leaf_wetness_probability_mean",
                  "winddirection_10m_dominant", "cloud_cover_mean"],
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch"
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_showers_sum = daily.Variables(0).ValuesAsNumpy()
    daily_weather_code = daily.Variables(1).ValuesAsNumpy()
    daily_snowfall_sum = daily.Variables(2).ValuesAsNumpy()
    daily_rain_sum = daily.Variables(3).ValuesAsNumpy()
    daily_precipitation_probability_max = daily.Variables(4).ValuesAsNumpy()
    daily_wind_speed_10m_max = daily.Variables(5).ValuesAsNumpy()
    daily_temperature_2m_max = daily.Variables(6).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(7).ValuesAsNumpy()
    daily_leaf_wetness_probability_mean = daily.Variables(8).ValuesAsNumpy()
    daily_winddirection_10m_dominant = daily.Variables(9).ValuesAsNumpy()
    daily_cloud_cover_mean = daily.Variables(10).ValuesAsNumpy()

    daily_data = {"date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    )}

    daily_data["showers_sum"] = daily_showers_sum
    daily_data["weather_code"] = daily_weather_code
    daily_data["snowfall_sum"] = daily_snowfall_sum
    daily_data["rain_sum"] = daily_rain_sum
    daily_data["precipitation_probability_max"] = daily_precipitation_probability_max
    daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["leaf_wetness_probability_mean"] = daily_leaf_wetness_probability_mean
    daily_data["winddirection_10m_dominant"] = daily_winddirection_10m_dominant
    daily_data["cloud_cover_mean"] = daily_cloud_cover_mean

    with open('./static/descriptions.json') as f:
        d = json.load(f)
        # d[f'{daily_data["weather_code"]}']

    template = loader.get_template('forecast.html')
    context = {
        'precipitation': d[f'{int(daily_data["weather_code"].max())}']
    }
    return HttpResponse(template.render(context, request))
