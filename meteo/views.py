from datetime import datetime

import openmeteo_requests
import geocoder
import json
import requests
from django.http import HttpResponse
from django.template import loader
import requests_cache
from requests_cache import CachedSession
from retry_requests import retry, TSession

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
    meteo_data = requests.get(api_request).json()
    temp = meteo_data['hourly']['temperature_2m'][current_hour]
    return temp

def get_weather(request):
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session: CachedSession | TSession = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 52.52,
        "longitude": 13.41,
        "daily": ["uv_index_clear_sky_max", "temperature_2m_max", "temperature_2m_min", "weather_code",
                  "precipitation_probability_max", "wind_speed_10m_max"],
        "current": "temperature_2m",
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch"
    }
    response = openmeteo.weather_api(url, params=params)[0]
    return format_weather_data(request, response)


def format_weather_data(request, response):
    current_temperature_2m = get_current_temp(response)
    daily_data = get_daily_data(response)
    with open('./static/descriptions.json') as f:
        d = json.load(f)
    max_weather_code = int(daily_data["weather_code"].max())
    rain = [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]
    snow_hail = [56, 57, 66, 67, 71, 73, 75, 77, 85, 85, 86, 96, 99]
    template = loader.get_template('forecast.html')
    context = {
        'max_weather_code': max_weather_code,
        'day_precipitation': d[str(max_weather_code)]['day']['description'],
        'night_precipitation': d[str(max_weather_code)]['night']['description'],
        'precipitation_probability_max': daily_data['precipitation_probability_max'].max(),
        'rain_alert': True if max_weather_code in rain else False,
        'snow_hail_alert': True if max_weather_code in snow_hail else False,
        'current_temp': current_temperature_2m,
        'uv_index': daily_data['uv_index_clear_sky_max'].max() if max_weather_code not in rain or snow_hail else 0,
        'temp_min': round(daily_data['temperature_2m_min'].min()),
        'temp_max': round(daily_data['temperature_2m_max'].max()),
        'wind_speed': round(daily_data['wind_speed_10m_max'].max())
    }
    return HttpResponse(template.render(context, request))


def get_daily_data(response):
    daily = response.Daily()
    daily_data = {
        "uv_index_clear_sky_max": daily.Variables(0).ValuesAsNumpy(),
        "temperature_2m_max": daily.Variables(1).ValuesAsNumpy(),
        "temperature_2m_min": daily.Variables(2).ValuesAsNumpy(),
        "weather_code": daily.Variables(3).ValuesAsNumpy(),
        "precipitation_probability_max": daily.Variables(4).ValuesAsNumpy(),
        "wind_speed_10m_max": daily.Variables(5).ValuesAsNumpy()
    }
    return daily_data


def get_current_temp(response):
    current = response.Current()
    current_temperature_2m = current.Variables(0).Value()
    return current_temperature_2m
