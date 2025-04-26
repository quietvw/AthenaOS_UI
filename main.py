#main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from flaskwebgui import FlaskUI, close_application
from datetime import datetime
import requests
from geopy.geocoders import Nominatim
from datetime import datetime

def get_coordinates(zip_code):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode({"postalcode": zip_code, "country": "USA"})
    if not location:
        raise Exception("Invalid ZIP code")
    return location.latitude, location.longitude


    lat, lon = get_coordinates(zip_code)

    # Get gridpoint and location info
    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    point_data = requests.get(point_url).json()
    city = point_data["properties"]["relativeLocation"]["properties"]["city"]
    state = point_data["properties"]["relativeLocation"]["properties"]["state"]
    forecast_url = point_data["properties"]["forecast"]

    # Get forecast data
    forecast_data = requests.get(forecast_url).json()
    current = forecast_data["properties"]["periods"][0]
    detailed = current["detailedForecast"].lower()

    # Determine condition
    if "rain" in detailed:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><line x1="16" y1="13" x2="16" y2="21"></line><line x1="8" y1="13" x2="8" y2="21"></line><line x1="12" y1="15" x2="12" y2="23"></line><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"></path></svg>'
    elif "snow" in detailed:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"></path><line x1="8" y1="16" x2="8.01" y2="16"></line><line x1="8" y1="20" x2="8.01" y2="20"></line><line x1="12" y1="18" x2="12.01" y2="18"></line><line x1="12" y1="22" x2="12.01" y2="22"></line><line x1="16" y1="16" x2="16.01" y2="16"></line><line x1="16" y1="20" x2="16.01" y2="20"></line></svg>'
    elif "clear" in detailed or "sunny" in detailed:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'
    else:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>'

    temperature = f"{current['temperature']}F"

    return {
        "location": f"{city}, {state}",
        "condition": condition,
        "temperature": temperature
    }

weather_cache = {
    "date": None,
    "data": {}
}

def fetch_weather(zip_code):
    today = datetime.now().date()

    # Check if we already cached today's weather for this ZIP
    if weather_cache["date"] == today and zip_code in weather_cache["data"]:
        return weather_cache["data"][zip_code]

    # Otherwise, fetch fresh data
    lat, lon = get_coordinates(zip_code)

    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    point_data = requests.get(point_url).json()
    city = point_data["properties"]["relativeLocation"]["properties"]["city"]
    state = point_data["properties"]["relativeLocation"]["properties"]["state"]
    forecast_url = point_data["properties"]["forecast"]

    forecast_data = requests.get(forecast_url).json()
    current = forecast_data["properties"]["periods"][0]
    detailed = current["detailedForecast"].lower()

    if "rain" in detailed:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><line x1="16" y1="13" x2="16" y2="21"></line><line x1="8" y1="13" x2="8" y2="21"></line><line x1="12" y1="15" x2="12" y2="23"></line><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"></path></svg>'
    elif "snow" in detailed:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"></path><line x1="8" y1="16" x2="8.01" y2="16"></line><line x1="8" y1="20" x2="8.01" y2="20"></line><line x1="12" y1="18" x2="12.01" y2="18"></line><line x1="12" y1="22" x2="12.01" y2="22"></line><line x1="16" y1="16" x2="16.01" y2="16"></line><line x1="16" y1="20" x2="16.01" y2="20"></line></svg>'
    elif "clear" in detailed or "sunny" in detailed:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'
    else:
        condition = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>'

    temperature = f"{current['temperature']}F"

    weather_info = {
        "location": f"{city}, {state}",
        "condition": condition,
        "temperature": temperature
    }

    # Update cache
    if weather_cache["date"] != today:
        weather_cache["date"] = today
        weather_cache["data"] = {}
    weather_cache["data"][zip_code] = weather_info

    return weather_info

app = FastAPI()

# Mounting default static files
app.mount("/public", StaticFiles(directory="dist/"))
templates = Jinja2Templates(directory="dist")



app.mount("/static", StaticFiles(directory="dist/static/"))

@app.get("/", response_class=HTMLResponse)
async def splash(request: Request):
    return templates.TemplateResponse("splash.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/lock", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("pin_protect.html", {"request": request})


@app.get("/music", response_class=HTMLResponse)
async def music(request: Request):
    return templates.TemplateResponse("music.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/call", response_class=HTMLResponse)
async def call(request: Request):
    return templates.TemplateResponse("call.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/settings_wifi", response_class=HTMLResponse)
async def wifi(request: Request):
    return templates.TemplateResponse("wifi_settings.html", {"request": request})

@app.get("/settings_time", response_class=HTMLResponse)
async def wifi(request: Request):
    return templates.TemplateResponse("time_settings.html", {"request": request})

@app.route("/close", methods=["GET"])
def close_window(*args, **kwargs):
    close_application()
    return "Window closing"

@app.get("/ws/current_time")
async def current_time():
    now = datetime.now().strftime("%I:%M %p")  # 12-hour format with AM/PM
    return JSONResponse(content={"time": now})

@app.get("/ws/current_weather")
async def current_weather():
    try:
        weather = fetch_weather("75072")
        return JSONResponse(content=weather)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

if __name__ == "__main__":

    FlaskUI(app=app, server="fastapi",width=960,
            height=640, port=15500).run()
