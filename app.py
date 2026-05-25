from flask import Flask, render_template, jsonify
import serial
import time
import threading

app = Flask(__name__)

# Config
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

# Global variable to store the latest reading
latest_moisture = "Connecting..."

def read_from_arduino():
    global latest_moisture
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for Arduino to reset
        print("Connected to Arduino!")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    latest_moisture = line
            time.sleep(0.1) # Small sleep to save CPU
    except Exception as e:
        latest_moisture = f"Error: {e}"

# Start the background thread BEFORE the app runs
thread = threading.Thread(target=read_from_arduino, daemon=True)
thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_reading')
def get_reading():
    return jsonify(moisture=latest_moisture)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)