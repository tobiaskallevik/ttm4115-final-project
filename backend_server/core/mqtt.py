import paho.mqtt.client as mqtt
import json
from django.conf import settings
from .models import Order


DRONE_STATUS_MAP = {
    'in_flight': 'in_transit',
    'arrived': 'arrived',
    'delivering': 'delivering',
    'waiting_pickup': 'loaded',
    'aborting': 'failed',
    'package_stuck': 'stuck',
}

def on_connect(client, userdata, flags, rc):
    print(f"Django connected to MQTT Broker with result code {rc}")
    client.subscribe("server")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if "drone_status" in payload:
            drone_status = payload["drone_status"]
            order_id = payload.get('id')
            mapped_status = DRONE_STATUS_MAP.get(drone_status)
            print(f"Drone Status update: {drone_status}")

            if mapped_status is None:
                return

            if order_id is None:
                return

            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                print(f"Order {order_id} not found for MQTT status update")
                return
            
            if order.status == 'delivered' and mapped_status == 'in_transit':
                return

            order.status = mapped_status
            order.save(update_fields=['status'])
                    
    except Exception as e:
        print(f"Error parsing MQTT message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def start_mqtt():
    try:
        client.connect(settings.MQTT_SERVER, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
        client.loop_start()
        print("MQTT Listener Started Successfully")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")