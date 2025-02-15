import serial.tools.list_ports
from flask import Flask, request, jsonify
from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType

app = Flask(__name__)

API_KEY = "DJKnkdwjnkjNEKJWFNWJKNKJENKLJVnlKVNWLKVNWLEVJNLEJnvELJVNLKEVNLEKVNLKVENLKVN"


vfd_details = {
    "VFDNONVEGEXH1": 5,
    "VFDNONVEGEXH2": 6,
    "VFDNONVEGFAH1": 11
}


# Auto-detect RS485 USB port
def find_usb_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"Detected Port: {port.device} - {port.description}")
        if "FT232" in port.description or "usbserial" in port.device or "USB" in port.device or "/dev/cu.usbserial" in port.device:
            print(f"✅ Using RS485 Adapter on: {port.device}")
            return port.device

    print("No USB-to-RS485 adapter found. Exiting.")
    return None  # Handle missing device properly

def execute_modbus_command(action, address, slave_id, value=None):
    usb_port = find_usb_port()
    print(usb_port)
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
                return {"success": False, "error": str(response)}
            return {"success": True, "value": response.registers[0]}

        elif action == "write":
            response = modbus_client.write_register(address=address, value=value, slave=slave_id)
            if response.isError():
                return {"success": False, "error": str(response)}
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
    if device_id not in list(vfd_details.keys()):
        return jsonify({'success': False, 'error': 'Device id wrong'}), 422

    data = execute_modbus_command("read", address=7, slave_id=vfd_details[device_id])
    if data['success'] is False:
        return jsonify(data), 422
    return jsonify({'success': True, "value": int(data['value'])/10}), 200


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
        if device_id not in list(vfd_details.keys()):
            return jsonify({'success': False, 'error': 'Device id wrong'}), 422

        if not isinstance(freq_value, int) or not (0 <= freq_value <= 50):
            return jsonify({"success": False, "error": "Invalid frequency value. Must be between 30-50 Hz"}), 422

        scaled_value = freq_value * 10
        data_execute = execute_modbus_command("write", address=1103, value=scaled_value, slave_id=vfd_details[device_id])
        if data_execute['success'] is True:
            return jsonify({'success': True, "written_value": int(data_execute['written_value'])/10}), 200
        return jsonify({'success': False, "error": data_execute['error']}), 422

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 422


@app.route('/')
def home():
    return jsonify({"status": "Modbus RTU Flask API is running!"}), 200

if __name__ == '__main__':

    print("🔄 Starting Flask Modbus RTU API...")
    app.run(host='0.0.0.0', port=8080)