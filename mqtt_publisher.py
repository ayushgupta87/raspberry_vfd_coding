import json
import time
import paho.mqtt.client as mqtt
import serial.tools.list_ports
from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType

# MQTT Configuration
MQTT_BROKER = "epvi-emqx.in"
MQTT_PORT = 1883
MQTT_TOPIC = "publish/*"

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set("enlog_sensors", "KJNekjncsdbksjvbskjvbKJDNSFUEORfiernlfljefnbkjBEKJVNEONVOEIVN")  # Set if authentication is required
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

vfd_details = {
    "VFDNONVEGEXH1": 5,
    "VFDNONVEGEXH2": 6,
    "VFDNONVEGFAH1": 11
}

def find_usb_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "FT232" in port.description or "usbserial" in port.device or "USB" in port.device or "/dev/cu.usbserial" in port.device:
            return port.device
    return None

usb_port = find_usb_port()

def execute_modbus_command(action, address, slave_id):
    """ Helper function to execute Modbus commands """
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
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        modbus_client.close()

def publish_modbus_to_mqtt():
    while True:
        for device_id in vfd_details.keys():
            data = execute_modbus_command("read", address=8, slave_id=vfd_details[device_id])
            if data['success']:
                amps = data["value"]
                send_value = {"deviceid":device_id,
                              "voltage":"250",
                              "current1":round(float(amps), 2)/10,
                              "current2":round(float(amps), 2)/10,
                              "current3":round(float(amps), 2)/10,
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
        time.sleep(120)

if __name__ == "__main__":
    print("🔄 Starting MQTT Publisher...")
    publish_modbus_to_mqtt()