import stmpy
import paho.mqtt.client as mqtt
from gpiozero import LED
import json
import time
import os

red_status_led = LED(13)    
yellow_status_led = LED(19) 
green_status_led = LED(26)  

class ChargingStation:
    def __init__(self):
        self.capacity = 2 
        self.drones = set() 
        self.mqtt_host = os.getenv('MQTT_SERVER', '10.126.236.206')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = self.on_message
        self.client.connect(self.mqtt_host, self.mqtt_port) 
        self.client.subscribe("charging")
        self.client.subscribe("server")
        self.client.loop_start()

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        action = payload.get('action')
        drone_id = payload.get('drone_id') or payload.get('id')

        if msg.topic == "server":
            drone_status = payload.get('drone_status')
            if drone_status == 'charging':
                action = 'drone_arriving'

        valid_triggers = ['available', 'full', 'drone_arriving', 'drone_charged', 'drone_leaving', 'end_charging']

        if action in ['drone_arriving', 'drone_leaving', 'end_charging'] and not drone_id:
            print(f'[Warning] Ignoring {action} without drone_id')
            return

        if action in valid_triggers:
            self.stm.send(action, args=[drone_id])


    def startup(self):
        print("startup() - Flashing LEDs")
        red_status_led.on()
        yellow_status_led.on()
        green_status_led.on()
        time.sleep(0.5)
        red_status_led.off()
        yellow_status_led.off()
        green_status_led.off()

    def count_drones(self):
        print(f"count_drones() - Current: {len(self.drones)}")
        if len(self.drones) >= self.capacity:
            self.stm.send('full')
        else:
            self.stm.send('available')

    def start_charging_all(self):
        print("start_charging() [Startup Phase]")
        if len(self.drones) > 0:
            yellow_status_led.on()

    def not_available(self):
        print("not_available() - RED ON, GREEN OFF")
        green_status_led.off()
        red_status_led.on()

    def available(self):
        print("available() - GREEN ON, RED OFF")
        red_status_led.off()
        green_status_led.on()

    def add_drone(self, drone_id):
        print(f"add_drone({drone_id})")
        if drone_id:
            self.drones.add(drone_id)

        if len(self.drones) >= self.capacity:
            self.stm.send('full')

    def start_charging(self, drone_id):
        print(f"start_charging({drone_id}) - YELLOW ON")
        yellow_status_led.on()

    def stop_charging(self, drone_id):
        print(f"stop_charging({drone_id})")
        if len(self.drones) <= 1: 
            print("No more drones charging - YELLOW OFF")
            yellow_status_led.off()

    def remove_drone(self, drone_id):
        print(f"remove_drone({drone_id})")
        was_full = len(self.drones) >= self.capacity
        if drone_id in self.drones:
            self.drones.remove(drone_id)
        if was_full and len(self.drones) < self.capacity:
            self.stm.send('available')

    def reject_drone(self, drone_id):
        print(f"reject_drone({drone_id}) - Station is Full!")


station = ChargingStation()

state_startup = {
    'name': 'Startup',
    'entry': 'startup; count_drones',
    'exit': 'start_charging_all'
}

state_available = {
    'name': 'Available',
    'entry': 'available',
    'exit': 'not_available',
    'drone_arriving': 'add_drone(*); start_charging(*)',
    'drone_charged': 'stop_charging(*)',
    'drone_leaving': 'stop_charging(*); remove_drone(*)',
    'end_charging': 'stop_charging(*); remove_drone(*)'
}

state_full = {
    'name': 'Full',
    'entry': 'not_available',
    'exit': 'available',
    'drone_arriving': 'reject_drone(*)',
    'drone_charged': 'stop_charging(*)',
    'drone_leaving': 'stop_charging(*); remove_drone(*)',
    'end_charging': 'stop_charging(*); remove_drone(*)'
}

t0 = {'source': 'initial', 'target': 'Startup'}
t1 = {'trigger': 'available', 'source': 'Startup', 'target': 'Available'}
t2 = {'trigger': 'full', 'source': 'Startup', 'target': 'Full'}
t3 = {'trigger': 'full', 'source': 'Available', 'target': 'Full'}
t4 = {'trigger': 'available', 'source': 'Full', 'target': 'Available'}


stm_charging = stmpy.Machine(
    name='stm_charging',
    transitions=[t0, t1, t2, t3, t4],
    states=[state_startup, state_available, state_full],
    obj=station
)
station.stm = stm_charging

driver = stmpy.Driver()
driver.add_machine(stm_charging)
driver.start()