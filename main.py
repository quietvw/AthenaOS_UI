from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, url_for
from datetime import datetime
import requests
from geopy.geocoders import Nominatim
import os
import re
import subprocess
import threading
import time

upgrade_log = []
upgrading_to_commit = None

app = Flask(__name__, static_folder="dist/static", template_folder="dist")

weather_cache = {
    "date": None,
    "data": {}
}
wifi_networks_cache = []
connecting_ssid = None  # Track currently connecting SSID

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception as e:
        print(f"Command failed {cmd}: {e}")
        return ""

def check_internet():
    return subprocess.run(["ping", "-c", "1", "-W", "1", "8.8.8.8"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def get_all_interfaces():
    return [iface for iface in os.listdir("/sys/class/net/") if iface != "lo"]

def get_active_interfaces():
    interfaces = []
    output = run_cmd(["ip", "-o", "link", "show", "up"])
    for line in output.splitlines():
        parts = line.split(": ")
        if len(parts) > 1:
            iface = parts[1].split('@')[0]
            if iface != "lo":
                interfaces.append(iface)
    return interfaces

def is_wireless(interface):
    return os.path.isdir(f"/sys/class/net/{interface}/wireless") or "wl" in interface

def get_wireless_interfaces():
    return [iface for iface in get_all_interfaces() if is_wireless(iface)]

def has_wifi_device():
    return bool(get_wireless_interfaces())

def wifi_enabled():
    return run_cmd(["nmcli", "radio", "wifi"]).lower() == "enabled"

def scan_wifi_networks():
    global connecting_ssid
    try:
        run_cmd(["nmcli", "device", "wifi", "rescan"])
        output = run_cmd(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"])

        ssid_map = {}
        lines = output.splitlines()

        for line in lines:
            parts = line.split(":")
            if len(parts) >= 4:
                in_use, ssid, signal, security = parts[:4]
                ssid = ssid.strip()
                if not ssid:
                    continue

                status = "connected" if in_use.strip() == "*" else "disconnected"

                # Show "connecting" if we are connecting to this SSID
                if connecting_ssid == ssid and status == "disconnected":
                    status = "connecting"

                network = {
                    "ssid": ssid,
                    "secure": security.strip() != "--",
                    "signal": int(signal.strip()),
                    "status": status
                }

                ssid_map[ssid] = network

        return sorted(ssid_map.values(), key=lambda x: x['signal'], reverse=True)
    except Exception as e:
        print(f"Wi-Fi scan failed: {e}")
        return []

def background_wifi_scanner():
    global wifi_networks_cache, connecting_ssid
    while True:
        wifi_networks_cache = scan_wifi_networks()
        if connecting_ssid:
            # Check if connection succeeded
            connected = any(net['ssid'] == connecting_ssid and net['status'] == "connected" for net in wifi_networks_cache)
            if connected:
                connecting_ssid = None
        time.sleep(5)

# Start scanner
scanner_thread = threading.Thread(target=background_wifi_scanner, daemon=True)
scanner_thread.start()

@app.route("/ws/net_wifi", methods=["GET", "POST"])
def net_wifi():
    global connecting_ssid
    try:
        if request.method == "POST":
            action = request.json.get("action")

            if action == "toggle_wifi":
                new_state = "off" if wifi_enabled() else "on"
                run_cmd(["nmcli", "radio", "wifi", new_state])
                return jsonify({"wifi_enabled": new_state == "on"})

            elif action == "connect":
                ssid = request.json.get("ssid")
                password = request.json.get("password", "")
                use_dhcp = request.json.get("use_dhcp", True)
                static_config = request.json.get("static_config", {})

                connect_cmd = ["nmcli", "device", "wifi", "connect", ssid]
                if password:
                    connect_cmd += ["password", password]
                connect_cmd += ["name", ssid]  # Add connection name explicitly
                run_cmd(connect_cmd)

                connecting_ssid = ssid

                if not use_dhcp and static_config:
                    run_cmd(["nmcli", "con", "mod", ssid,
                             "ipv4.addresses", static_config["ip"],
                             "ipv4.gateway", static_config["gateway"],
                             "ipv4.dns", static_config["dns"],
                             "ipv4.method", "manual"])
                    run_cmd(["nmcli", "con", "up", ssid])

                return jsonify({"status": "connecting"})

            elif action == "disconnect":
                ssid = request.json.get("ssid")
                run_cmd(["nmcli", "con", "down", "id", ssid])
                return jsonify({"status": "disconnected"})

        return jsonify({
            "has_wifi": has_wifi_device(),
            "wifi_enabled": wifi_enabled(),
            "networks": wifi_networks_cache
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    return render_template("splash.html", message="Starting AthenaOS...", href="/lock")

@app.route("/reboot")
def splash_reboot():
    # Start reboot after small delay, so page can render first
    threading.Thread(target=delayed_command, args=(["reboot"],)).start()
    return render_template("splash.html", message="AthenaOS is rebooting...", href="/reboot")

@app.route("/shutdown")
def splash_shutdown():
    # Start shutdown after small delay, so page can render first
    threading.Thread(target=delayed_command, args=(["shutdown", "now"],)).start()
    return render_template("splash.html", message="AthenaOS is shutting down...", href="/shutdown")

def delayed_command(cmd):
    time.sleep(2)  # Wait 2 seconds to allow the page to render
    subprocess.run(cmd)

@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/lock")
def lock():
    return render_template("pin_protect.html")



upgrade_log = []
upgrading_to_commit = None


def run_command(cmd, cwd):
    global upgrade_log
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in process.stdout:
            upgrade_log.append(line.strip())
        process.wait()
        if process.returncode != 0:
            upgrade_log.append(f"❌ Command failed with return code {process.returncode}")
    except Exception as e:
        upgrade_log.append(f"❌ Exception: {str(e)}")

def background_upgrade():
    global upgrade_log
    try:
        upgrade_log.append("🔵 Fetching latest updates from remote...")
        run_command(['git', 'fetch', '--all'], cwd='/home/athenaos/AthenaOS_UI')

        upgrade_log.append("🔵 Resetting to latest origin/main...")
        run_command(['git', 'reset', '--hard', 'origin/main'], cwd='/home/athenaos/AthenaOS_UI')

        upgrade_log.append("🔵 Installing updated Python requirements...")
        run_command(
            ['pip3', 'install', '-r', 'requirements.txt', '--break-system-packages'],
            cwd='/home/athenaos/AthenaOS_UI'
        )
        upgrade_log.append("🔵 Running system update...")
        run_command(['apt', 'update', '-y'], cwd='/home/athenaos/AthenaOS_UI')
        run_command(['apt', 'upgrade', '-y'], cwd='/home/athenaos/AthenaOS_UI')
        upgrade_log.append("✅ Update complete. AthenaOS UI is now up to date.")
    except Exception as e:
        upgrade_log.append(f"❌ Fatal error during upgrade: {e}")


@app.route("/force_update", methods=["GET"])
def force_update():
    global upgrading_to_commit, upgrade_log
    upgrade_log = []  # clear previous logs

    try:
        # Fetch latest remote commit
        upgrading_to_commit = subprocess.check_output(
            ['git', 'rev-parse', 'origin/main'],
            cwd='/home/athenaos/AthenaOS_UI'
        ).decode('utf-8').strip()
    except Exception as e:
        upgrading_to_commit = "Unknown"
        upgrade_log.append(f"Failed to fetch remote commit: {e}")

    # Start background upgrade thread
    thread = threading.Thread(target=background_upgrade)
    thread.start()

    # Redirect immediately
    return redirect("/upgrade_process")

@app.route("/upgrade_process")
def upgrade_process():
    global upgrade_log, upgrading_to_commit
    return render_template("update.html", logs=upgrade_log, commit=upgrading_to_commit)

@app.route("/upgrade_logs")
def upgrade_logs():
    global upgrade_log
    return jsonify({"logs": upgrade_log})

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

@app.route("/settings_dev")
def settings_dev():
    return render_template("dev_settings.html")


@app.route("/settings_about")
def settings_about():
    try:
        # Get current running commit (local repo HEAD)
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd='/home/athenaos/AthenaOS_UI'
        ).decode('utf-8').strip()

        # Fetch latest from origin
        subprocess.check_call(
            ['git', 'fetch'],
            cwd='/home/athenaos/AthenaOS_UI'
        )

        # Get latest commit from remote (origin/main)
        latest_commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'origin/main'],
            cwd='/home/athenaos/AthenaOS_UI'
        ).decode('utf-8').strip()

    except Exception as e:
        print(f"Error getting git commit info: {e}")
        commit_hash = "Unknown"
        latest_commit_hash = "Unknown"

    return render_template(
        "setting_software.html", 
        commit_hash=commit_hash, 
        latest_commit_hash=latest_commit_hash
    )


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
    app.run(host="127.0.0.1", port=15500, debug=True)
