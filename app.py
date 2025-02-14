import json
# import threading
import time

import serial.tools.list_ports
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType

app = Flask(__name__)

API_KEY = "DJKnkdwjnkjNEKJWFNWJKNKJENKLJVnlKVNWLKVNWLEVJNLEJnvELJVNLKEVNLEKVNLKVENLKVN"

# modbus_lock = threading.Lock()

vfd_details = {
    "VFDNV1": 5,
    "VFDNV2": 6,
    "VFDNV3": 11
}


# MQTT Configuration
MQTT_BROKER = "epvi-emqx.in"  # Change to your MQTT broker
MQTT_PORT = 1883

MQTT_TOPIC = "publish/*"

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set("enlog_sensors", "KJNekjncsdbksjvbskjvbKJDNSFUEORfiernlfljefnbkjBEKJVNEONVOEIVN")  # Set if authentication is required
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)


# Auto-detect RS485 USB port
def find_usb_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"Detected Port: {port.device} - {port.description}")
        if "FT232" in port.description or "usbserial" in port.device or "USB" in port.device:
            print(f"✅ Using RS485 Adapter on: {port.device}")
            return port.device

    print("No USB-to-RS485 adapter found. Exiting.")
    return None  # Handle missing device properly

usb_port = find_usb_port()

def execute_modbus_command(action, address, slave_id, value=None):
    """ Helper function to create Modbus connection, execute, and close it """

    modbus_client = ModbusSerialClient(
        port=usb_port,
        baudrate=9600,
        stopbits=1,
        bytesize=8,
        parity='N',
        timeout=2,
        framer=FramerType.RTU
    )

    if not modbus_client.connect():
        return {"success": False, "error": "Failed to connect to Modbus device"}

    try:
        if action == "read":
            response = modbus_client.read_holding_registers(address=address, count=1, slave=slave_id)
            if response.isError():
                return {"success": False, "details": str(response)}
            return {"success": True, "value": response.registers[0]}

        elif action == "write":
            response = modbus_client.write_register(address=address, value=value, slave=slave_id)
            if response.isError():
                return {"success": False, "details": str(response)}
            return {"success": True, "written_value": value}

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        modbus_client.close()  # Close connection after execution


@app.route('/get_freq', methods=['GET'])
def get_frequency():
    device_id = request.args.get("device_id")
    api_key = request.args.get("api_key")

    if api_key != API_KEY:
        return jsonify({'success': False, 'error': 'Auth Error'}), 422

    if device_id is None:
        return jsonify({'success': False, 'error': 'Device id not added'}), 422
    if device_id not in ['VFDNV1', 'VFDNV2', 'VFDNV3']:
        return jsonify({'success': False, 'error': 'Device id wrong'}), 422

    data = execute_modbus_command("read", address=7, slave_id=vfd_details[device_id])
    if data['success'] is False:
        return jsonify(data), 422
    return jsonify(data), 200


@app.route('/set_freq', methods=['POST'])
def set_frequency():
    """ Write frequency value to Modbus register (address 1103) """
    try:
        data = request.json
        freq_value = data.get("frequency")
        device_id = data.get("device_id")
        api_key = data.get("api_key")

        if api_key != API_KEY:
            return jsonify({'success': False, 'error': 'Auth Error'}), 422

        if device_id is None:
            return jsonify({'success': False, 'error': 'Device id not added'}), 422
        if device_id not in ['VFDNV1', 'VFDNV2', 'VFDNV3']:
            return jsonify({'success': False, 'error': 'Device id wrong'}), 422

        if not isinstance(freq_value, int) or not (0 <= freq_value <= 50):
            return jsonify({"success": False, "error": "Invalid frequency value. Must be between 30-50 Hz"}), 422

        scaled_value = freq_value * 10
        return jsonify(execute_modbus_command("write", address=1103, value=scaled_value, slave_id=vfd_details[device_id])), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 422


@app.route('/')
def home():
    return jsonify({"status": "Modbus RTU Flask API is running!"}), 200


def publish_modbus_to_mqtt():
    while True:
        for device_id in vfd_details.keys():
            data = execute_modbus_command("read", address=8, slave_id=vfd_details[device_id])
            if data['success'] is True:
                amps = data.get("value")
                send_value = {"deviceid":device_id,
                              "voltage":"250",
                              "current1":round(float(amps), 2),
                              "current2":round(float(amps), 2),
                              "current3":round(float(amps), 2),
                              "current4":"0.00",
                              "current5":"0.00",
                              "current6":"0.00",
                              "status":"111111",
                              "freq":40,"data":"live"
                              }

                mqtt_client.publish(MQTT_TOPIC.replace("*", device_id), json.dumps(send_value))
                print(f"📡 Published Frequency {amps}A to {MQTT_TOPIC}")
            else:
                print(f"⚠️ Modbus Read Failed: {data.get('error')}")
        time.sleep(40)  # Wait 40 seconds before next read


if __name__ == '__main__':

    # mqtt_thread = threading.Thread(target=publish_modbus_to_mqtt, daemon=True)
    # mqtt_thread.start()

    print("🔄 Starting Flask Modbus RTU API...")
    app.run(host='0.0.0.0', port=8000, debug=True)