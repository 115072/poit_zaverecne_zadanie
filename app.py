from flask import Flask, render_template, jsonify, request
import serial
import time
import threading

app = Flask(__name__)

# Config
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

# Global variables
latest_moisture = 0
regulation_limit = 500  # Default value
pump_status = "OFF"

def read_from_arduino():
    global latest_moisture, pump_status
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("Connected to Arduino!")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line.isdigit(): # Ensure it's a number
                    latest_moisture = int(line)
                    
                    # Logic for the Pump
                    if latest_moisture < regulation_limit:
                        pump_status = "ON (Watering...)"
                    else:
                        pump_status = "OFF (Soil is wet enough)"
                        
            time.sleep(0.1)
    except Exception as e:
        print(f"Error: {e}")

# Start background thread
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
    new_limit = data.get('limit')
    if new_limit is not None:
        regulation_limit = int(new_limit)
        return jsonify(status="success", new_limit=regulation_limit)
    return jsonify(status="error"), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)