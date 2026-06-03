from flask import Flask, render_template, jsonify, request
import serial
import time
import threading
import mysql.connector
import json
import os

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
session_buffer = [] # Temporary storage for the current session

# --- ARDUINO WORKER ---
def background_worker():
    global latest_moisture, pump_status, is_recording, current_session_id, session_buffer
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line.isdigit():
                    latest_moisture = int(line)
                    
                    if latest_moisture < regulation_limit:
                        ser.write(b'1')
                        pump_status = "ON"
                    else:
                        ser.write(b'0')
                        pump_status = "OFF"
                    
                    if is_recording:
                        # 1. Save to MySQL immediately
                        save_reading_db(current_session_id, latest_moisture, pump_status)
                        
                        # 2. Add to RAM buffer (to be saved to TXT later)
                        session_buffer.append({
                            "timestamp": time.strftime('%H:%M:%S'),
                            "moisture": latest_moisture,
                            "pump": pump_status
                        })

            time.sleep(1) 
    except Exception as e:
        print(f"Serial Error: {e}")

def save_reading_db(session_id, val, pump):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO readings (session_id, moisture, pump_state) VALUES (%s, %s, %s)", 
                       (session_id, val, pump))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    return jsonify(moisture=latest_moisture, limit=regulation_limit, pump=pump_status, recording=is_recording)

@app.route('/start_monitoring', methods=['POST'])
def start_mon():
    global is_recording, current_session_id, session_buffer
    session_buffer = [] # Clear buffer for new session
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
    if is_recording:
        # Save the entire buffer as ONE line in logs.txt
        if session_buffer:
            session_data = {
                "id": current_session_id,
                "date": time.strftime('%Y-%m-%d %H:%M:%S'),
                "readings": session_buffer
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(session_data) + "\n")
        
        # Update MySQL end time
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET end_time = NOW() WHERE id = %s", (current_session_id,))
        conn.commit()
        conn.close()

    is_recording = False
    current_session_id = None
    return jsonify(status="stopped")

@app.route('/list_txt_sessions')
def list_txt_sessions():
    sessions = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for idx, line in enumerate(f):
                data = json.loads(line)
                sessions.append({"index": idx, "id": data['id'], "date": data['date']})
    return jsonify(sessions)

@app.route('/get_txt_detail/<int:line_idx>')
def get_txt_detail(line_idx):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            if line_idx < len(lines):
                return jsonify(json.loads(lines[line_idx]))
    return jsonify({"error": "Not found"}), 404

# (Other routes list_sessions, get_session_details, set_limit remain the same)
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
    cursor.execute("SELECT timestamp, moisture, pump_state FROM readings WHERE session_id = %s", (sid,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

@app.route('/set_limit', methods=['POST'])
def set_limit():
    global regulation_limit
    regulation_limit = int(request.get_json().get('limit', 500))
    return jsonify(status="success")

if __name__ == '__main__':
    threading.Thread(target=background_worker, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)