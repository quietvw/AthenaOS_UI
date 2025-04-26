from flask import Flask, render_template, jsonify, send_from_directory
from datetime import datetime
import requests
from geopy.geocoders import Nominatim
import os

app = Flask(__name__, static_folder="dist/static", template_folder="dist")

weather_cache = {
    "date": None,
    "data": {}
}

def get_coordinates(zip_code):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode({"postalcode": zip_code, "country": "USA"})
    if not location:
        raise Exception("Invalid ZIP code")
    return location.latitude, location.longitude

def fetch_weather(zip_code):
    today = datetime.now().date()

    if weather_cache["date"] == today and zip_code in weather_cache["data"]:
        return weather_cache["data"][zip_code]

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

    if weather_cache["date"] != today:
        weather_cache["date"] = today
        weather_cache["data"] = {}
    weather_cache["data"][zip_code] = weather_info

    return weather_info

# -------------------------
#  Routes
# -------------------------

@app.route("/")
def splash():
    return render_template("splash.html")

@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/lock")
def lock():
    return render_template("pin_protect.html")

@app.route("/music")
def music():
    return render_template("music.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route("/call")
def call():
    return render_template("call.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/settings_wifi")
def settings_wifi():
    return render_template("wifi_settings.html")

@app.route("/settings_time")
def settings_time():
    return render_template("time_settings.html")

@app.route("/ws/current_time")
def current_time():
    now = datetime.now().strftime("%I:%M %p")
    return jsonify({"time": now})

@app.route("/ws/current_weather")
def current_weather():
    try:
        weather = fetch_weather("75072")
        return jsonify(weather)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# -------------------------
# Serve static manually if needed
# -------------------------
@app.route("/public/<path:filename>")
def public_files(filename):
    return send_from_directory("dist", filename)

# -------------------------
# Start the server
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=15500, debug=True)
