from flask import Flask, render_template, jsonify, request
import serial
import time
import threading
import mysql.connector

app = Flask(__name__)

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
db_config = {
    'host': 'localhost',
    'user': 'garden_user',      # Using the new user
    'password': 'garden_pass',  # Using the new password
    'database': 'smart_garden'
}

latest_moisture = 0
regulation_limit = 500
pump_status = "OFF"
current_session_id = None
is_recording = False

# --- ARDUINO WORKER ---
def background_worker():
    global latest_moisture, pump_status, is_recording, current_session_id
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
                    
                    if is_recording and current_session_id:
                        save_reading(current_session_id, latest_moisture, pump_status)

            time.sleep(1) 
    except Exception as e:
        print(f"Serial Error: {e}")

def save_reading(session_id, val, pump):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO readings (session_id, moisture, pump_state) VALUES (%s, %s, %s)", 
                       (session_id, val, pump))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB Insert Error: {e}")

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    return jsonify(moisture=latest_moisture, limit=regulation_limit, pump=pump_status, recording=is_recording)

@app.route('/start_monitoring', methods=['POST'])
def start_mon():
    global is_recording, current_session_id
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
    global is_recording, current_session_id
    if current_session_id:
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