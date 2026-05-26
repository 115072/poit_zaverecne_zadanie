from flask import Flask, render_template, jsonify, request
import serial
import time
import threading

app = Flask(__name__)

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

latest_moisture = 0
regulation_limit = 500
pump_status = "OFF"

def read_from_arduino():
    global latest_moisture, pump_status
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line and line.isdigit():
                    latest_moisture = int(line)
                    # Simple Pump Logic
                    if latest_moisture < regulation_limit:
                        pump_status = "ON"
                    else:
                        pump_status = "OFF"
            time.sleep(0.1)
    except Exception as e:
        print(f"Serial error: {e}")

thread = threading.Thread(target=read_from_arduino, daemon=True)
thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_reading')
def get_reading():
    return jsonify(
        moisture=latest_moisture,
        limit=regulation_limit,
        pump=pump_status
    )

@app.route('/set_limit', methods=['POST'])
def set_limit():
    global regulation_limit
    data = request.get_json()
    regulation_limit = int(data.get('limit', 500))
    return jsonify(status="success", new_limit=regulation_limit)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)