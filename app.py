from flask import Flask, render_template, jsonify, request
import serial
import time
import threading

app = Flask(__name__)

# Config - Change to /dev/ttyUSB0 if ACM0 doesn't work
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 9600

# Global Variables
latest_moisture = 0
regulation_limit = 500
pump_status = "OFF"

def background_worker():
    global latest_moisture, pump_status, regulation_limit
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for Arduino to reset

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line.isdigit():
                    latest_moisture = int(line)
                    
                    # Logic: Control the pump based on the limit
                    if latest_moisture < regulation_limit:
                        ser.write(b'1') 
                        pump_status = "ON"
                    else:
                        ser.write(b'0') 
                        pump_status = "OFF"

            time.sleep(0.1)
    except Exception as e:
        print(f"Serial Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    # Sends the current values to the webpage
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
    return jsonify(status="success")

if __name__ == '__main__':
    # Start the background thread to talk to Arduino
    threading.Thread(target=background_worker, daemon=True).start()
    # Start the Flask web server
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)