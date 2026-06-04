from flask import Flask, render_template, jsonify, request
import serial, time, threading, mysql.connector, json, os

app = Flask(__name__)

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
LOG_FILE = "logs.txt"
db_config = {
    'host': 'localhost', 
    'user': 'garden_user', 
    'password': 'garden_pass', 
    'database': 'smart_garden'
}

latest_moisture = 0
regulation_limit = 500
pump_status = "OFF"
current_session_id = None
is_recording = False
hardware_enabled = False
session_buffer = []

# --- ARDUINO WORKER ---
def background_worker():
    global latest_moisture, pump_status, is_recording, current_session_id, session_buffer, hardware_enabled
    ser = None
    last_sent_cmd = "" 
    last_hw_state = False # To track if we already sent 'A' or 'Q'

    while True:
        try:
            if ser is None:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
                time.sleep(2)

            if hardware_enabled:
                # Only send 'A' once when toggled
                if last_hw_state == False:
                    ser.write(b'A')
                    last_hw_state = True
                
                if ser.in_waiting > 0:
                    raw_data = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if "<" in raw_data and ">" in raw_data:
                        try:
                            clean_val = raw_data.split("<")[1].split(">")[0]
                            latest_moisture = int(clean_val)
                            
                            
                            if latest_moisture < regulation_limit:
                                if last_sent_cmd != "1":
                                    ser.write(b'1')
                                    last_sent_cmd = "1"
                                pump_status = "ON"
                            else:
                                if last_sent_cmd != "0":
                                    ser.write(b'0')
                                    last_sent_cmd = "0"
                                pump_status = "OFF"

                            if is_recording:
                                save_reading_db(current_session_id, latest_moisture, pump_status, regulation_limit)
                                session_buffer.append({
                                    "timestamp": time.strftime('%H:%M:%S'), 
                                    "moisture": latest_moisture, 
                                    "pump": pump_status,
                                    "limit": regulation_limit 
                                })
                        except (ValueError, IndexError):
                            pass
            else:
                # Only send 'Q' once when toggled off
                if last_hw_state == True:
                    if ser: ser.write(b'Q')
                    last_hw_state = False
                
                latest_moisture = 0
                pump_status = "OFF"
                last_sent_cmd = ""

            time.sleep(0.1) 
        except Exception as e:
            print(f"Serial Error: {e}")
            ser = None
            time.sleep(2)


# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/toggle_hardware', methods=['POST'])
def toggle_hw():
    global hardware_enabled
    hardware_enabled = request.get_json().get('enabled', False)
    return jsonify(status="success")

@app.route('/get_data') # <-- Fixed: removed colon
def get_data():
    return jsonify(moisture=latest_moisture, limit=regulation_limit, pump=pump_status, recording=is_recording, hardware=hardware_enabled)

@app.route('/start_monitoring', methods=['POST'])
def start_mon():
    global is_recording, current_session_id, session_buffer
    if not hardware_enabled: return jsonify(status="error"), 400
    session_buffer = []
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (reg_limit) VALUES (%s)", (regulation_limit,))
    conn.commit()
    current_session_id = cursor.lastrowid
    is_recording = True
    conn.close()
    return jsonify(status="started")

@app.route('/stop_monitoring', methods=['POST'])
def stop_mon():
    global is_recording, current_session_id, session_buffer
    if is_recording and session_buffer:
        data = {"id": current_session_id, "date": time.strftime('%Y-%m-%d %H:%M:%S'), "readings": session_buffer}
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(data) + "\n")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET end_time = NOW() WHERE id = %s", (current_session_id,))
        conn.commit()
        conn.close()
    is_recording = False
    current_session_id = None
    return jsonify(status="stopped")

@app.route('/list_sessions')
def list_sessions():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, start_time FROM sessions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

@app.route('/get_session_details/<int:sid>')
def get_details(sid):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT timestamp, moisture, pump_state, reg_limit FROM readings WHERE session_id = %s", (sid,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

@app.route('/list_txt_sessions')
def list_txt():
    sessions = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for idx, line in enumerate(f):
                try:
                    d = json.loads(line)
                    sessions.append({"index": idx, "id": d.get('id'), "date": d.get('date')})
                except: continue
    return jsonify(sessions)

@app.route('/get_txt_detail/<int:idx>')
def get_txt(idx):
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
        return jsonify(json.loads(lines[idx]))

@app.route('/set_limit', methods=['POST'])
def set_limit():
    global regulation_limit
    regulation_limit = int(request.get_json().get('limit', 500))
    return jsonify(status="success")

if __name__ == '__main__':
    threading.Thread(target=background_worker, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)