from flask import Flask, render_template, request, redirect, url_for, jsonify
import time, os, sys, json

# --- robuuste import van SensorDataProducer ---
try:
    # pakket-structuur: scripts/ClassSensorDataProducerE/SensorDataProducer.py
    from scripts.ClassSensorDataProducerE import SensorDataProducer
except Exception:
    try:
        # module: scripts/ClassSensorDataProducerE.py (of __init__.py export)
        from scripts.ClassSensorDataProducerE import SensorDataProducer
    except Exception:
        # lokaal bestand: ClassSensorDataProducerE.py (zoals geüpload)
        from scripts.ClassSensorDataProducerE import SensorDataProducer

app = Flask(__name__)
app.secret_key = "dev"

# config.json file settings
CONFIG_FILE = os.pat.join(os.path.dirname(__file__), "config.json")

# Config defaults, will be overriden by config.json if present
config = {
    "qe_min": 0, "qe_max": 180,
    "qh": 0,     # target yaw (°)
    "speed": 20, # °/s simulatie
    "upp_varia": 0,
    "start_upp_varia": 20,
    "start_boost": 20,
    "delta_boost": 0,
    "gain_boost": 0
}

def load_config_from_file():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    config.update(data)
                    print(f"[OK] Config loaded from {CONFIG_FILE}")
        except Exception as e:
            print(f"[WARN] Failed to load {CONFIG_FILE}: {e}")

def save_config_to_file(cfg: dict):
    # atomic write: write to temp then replace
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_FILE)
    print(f"[OK] Config saved to {CONFIG_FILE}")

# Load persisted settings (if any)
load_config_from_file()

I2C_BUS = 2  
start_time = time.time()
sensor = None
last_sample = {"yaw": 0.0, "pitch": 0.0}

def get_sensor():
    global sensor
    if sensor is None and SensorDataProducer is not None:
        try:
            sensor = SensorDataProducer(i2c_bus_number=I2C_BUS)
            print("[OK] SensorDataProducer geïnitialiseerd")
        except Exception as e:
            print(f"[WARN] Sensor init mislukt, fallback simulatie: {e}")
            sensor = None
    return sensor

@app.route("/", methods=["GET", "POST"])
def index():
    global start_time
    if request.method == "POST":
        def readf(name, default):
            try:
                return float(request.form.get(name, default))
            except Exception:
                return default

        config["qe_min"] = readf("qe_min", config["qe_min"])
        config["qe_max"] = readf("qe_max", config["qe_max"])
        config["qh"]     = readf("qh",     config["qh"])
        config["speed"]  = readf("speed",  config["speed"])
        config["upp_varia"]       = readf("upp_varia",       config["upp_varia"])
        config["start_upp_varia"] = readf("start_upp_varia", config["start_upp_varia"])
        config["start_boost"]     = readf("start_boost",     config["start_boost"])
        config["delta_boost"]     = readf("delta_boost",     config["delta_boost"])
        config["gain_boost"]      = readf("gain_boost",      config["gain_boost"])

        if config["qe_min"] > config["qe_max"]:
            config["qe_min"], config["qe_max"] = config["qe_max"], config["qe_min"]

        start_time = time.time()  # reset simulatieklok
        save_config_to_file(config) # persist immediately 

        return redirect(url_for("index"))

    return render_template("config.html", cfg=config)

# ---------- NIEUWE ENDPOINTS ----------
@app.post("/api/start")
def api_safe():
    data = request.get_json(silent=True) or {}
    def to_float(val, default):
        try:
            return float(val)
        except Exception:
            return default
        
    # merge 
    for key in ["qe_min","qe_max","qh","speed","upp_varia","start_upp_varia","start_boost","delta_boost","gain_boost"]:
        if key in data:
            config[key] = to_float(data[key], config[key])

    # sanity
    if config["qe_min"] > config["qe_max"]:
        config["qe_min"], config["qe_max"] = config["qe_max"], config["qe_min"]

    save_config_to_file(config)
    return jsonify({"ok": True, "config": config})

# --------------- Existing endpoints
@app.post("/api/start")
def api_start():
    s = get_sensor()
    if s is None:
        return jsonify({"ok": False, "state": "error", "message": "Sensor unavailable"}), 503
    s.start()
    return jsonify({"ok": True, "state": "running"})

@app.post("/api/stop")
def api_stop():
    s = get_sensor()
    if s is None:
        return jsonify({"ok": False, "state": "error", "message": "Sensor unavailable"}), 503
    s.stop()
    return jsonify({"ok": True, "state": "stopped"})

@app.post("/api/tare")
def api_tare():
    s = get_sensor()
    if s is None:
        return jsonify({"ok": False, "state": "error", "message": "Sensor unavailable"}), 503
    what = request.args.get("what", "all")
    try:
        s.tare(what)
        return jsonify({"ok": True, "state": "running" if s.is_running() else "stopped", "tared_at": s.last_tare_iso()})
    except ValueError as e:
        return jsonify({"ok": False, "state": "error", "message": str(e)}), 400

@app.get("/api/point")
def api_point():
    """
    X = yaw (sensor)
    Y = pitch (sensor)
    Groene zone centreert rond target 'qh' (±10°).
    """
    s = get_sensor()
    yaw = None
    pitch = None
    running = False

    if s is not None:
        try:
            data = s.read()  # {"yaw","pitch","running",...}
            yaw = float(data.get("yaw"))
            pitch = float(data.get("pitch"))
            running = bool(data.get("running", False))
            last_sample["yaw"], last_sample["pitch"] = yaw, pitch
        except Exception as e:
            print(f"[WARN] sensor.read() faalde: {e}")

    # Fallbacks
    if yaw is None or pitch is None:
        if last_sample["yaw"] != 0.0 or last_sample["pitch"] != 0.0:
            yaw, pitch = last_sample["yaw"], last_sample["pitch"]
        else:
            # pure simulatie
            t = time.time() - start_time
            yaw = float(config["qh"])
            pitch = float(config["qe_min"]) + float(config["speed"]) * t
            if pitch > float(config["qe_max"]):
                pitch = float(config["qe_max"])

    return jsonify({
        "yaw": yaw,
        "pitch": pitch,
        "qh": float(config["qh"]),
        "pitch_min": 0.0,
        "pitch_max": 180.0,
        "running": running
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
