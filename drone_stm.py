import stmpy
import paho.mqtt.client as mqtt
from sense_hat import SenseHat
import time
import json
import pygame  
import os
import threading

sense = SenseHat()
pygame.mixer.init()

class Drone:
    def __init__(self):
        self.current_order_id = None
        self.drone_id = os.getenv('DRONE_ID', 'drone-1')
        self.departure_destination = 'pickup'
        self.mqtt_host = os.getenv('MQTT_SERVER', '10.126.236.206')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.current_animation = None
        self.anim_thread = None
        self.shake_thread = None
        self.stop_shake = False
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = self.on_message
        self.client.connect(self.mqtt_host, self.mqtt_port)
        self.client.subscribe("drone")
        self.client.loop_start()

    def start_animation(self, anim_name):
        self.current_animation = anim_name
        if self.anim_thread is None or not self.anim_thread.is_alive():
            self.anim_thread = threading.Thread(target=self._animation_loop, daemon=True)
            self.anim_thread.start()

    def stop_animation(self):
        self.current_animation = None

    def _animation_loop(self):
        O = [0, 0, 0]      
        W = [255, 255, 255] 
        B = [0, 0, 255]     
        G = [0, 255, 0]    
        R = [255, 0, 0]    

        prop_frame_1 = [
            O,O,O,W,W,O,O,O,
            O,O,O,W,W,O,O,O,
            O,O,O,O,O,O,O,O,
            W,W,O,B,B,O,W,W,
            W,W,O,B,B,O,W,W,
            O,O,O,O,O,O,O,O,
            O,O,O,W,W,O,O,O,
            O,O,O,W,W,O,O,O
        ]
        
        prop_frame_2 = [
            W,W,O,O,O,O,W,W,
            W,W,O,O,O,O,W,W,
            O,O,O,O,O,O,O,O,
            O,O,O,B,B,O,O,O,
            O,O,O,B,B,O,O,O,
            O,O,O,O,O,O,O,O,
            W,W,O,O,O,O,W,W,
            W,W,O,O,O,O,W,W
        ]

        bat_frame_1 = [
            O,O,O,W,W,O,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,W,W,W,O,O,
            O,O,O,O,O,O,O,O
        ]
        bat_frame_2 = [
            O,O,O,W,W,O,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,G,G,W,O,O,
            O,O,W,G,G,W,O,O,
            O,O,W,W,W,W,O,O,
            O,O,O,O,O,O,O,O
        ]
        bat_frame_3 = [
            O,O,O,W,W,O,O,O,
            O,O,W,O,O,W,O,O,
            O,O,W,G,G,W,O,O,
            O,O,W,G,G,W,O,O,
            O,O,W,G,G,W,O,O,
            O,O,W,G,G,W,O,O,
            O,O,W,W,W,W,O,O,
            O,O,O,O,O,O,O,O
        ]

        while self.current_animation:
            if self.current_animation == 'flying':
                sense.set_pixels(prop_frame_1)
                time.sleep(0.1)
                if self.current_animation != 'flying': break
                sense.set_pixels(prop_frame_2)
                time.sleep(0.1)
                
            elif self.current_animation == 'charging':
                sense.set_pixels(bat_frame_1)
                time.sleep(0.5)
                if self.current_animation != 'charging': break
                sense.set_pixels(bat_frame_2)
                time.sleep(0.5)
                if self.current_animation != 'charging': break
                sense.set_pixels(bat_frame_3)
                time.sleep(0.5)
            else:
                time.sleep(0.1)

    def play_sound(self, filename):
        try:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            print(f"Playing {filename}")
        except Exception as e:
            print(f"Error playing sound: {e}")

    def stop_sound(self):
            try:
                pygame.mixer.music.stop()
                print("Stopped sound")
            except Exception as e:
                print(f"Error stopping sound: {e}")

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        action = payload.get('action')
        order_id = payload.get('id')
        if order_id is not None:
            self.current_order_id = order_id

        if action == 'resume_to_restaurant':
            self.departure_destination = 'pickup'
            self.stm.send('order')
            return

        if action == 'resume_to_customer':
            self.departure_destination = 'delivery'
            self.stm.send('order')
            return

        if action == 'order':
            self.departure_destination = 'pickup'
        
        if action == 'package_stuck' and self.stm.state == 'Delivering':
            print("Package is stuck! Try to shake it free")
            self.start_shake_test()
            return
  
        valid_triggers = [
            'order',
            'at_dest_pickup',
            'pickup_complete',
            'at_dest_delivery',
            'presence_confirmed',
            'delivered',
            'low_battery',
            'routed_to_station',
            'cancel',
            'timeout',
            'package_stuck',
            'at_dest_charging',
        ]
        if action in valid_triggers:
            self.stm.send(action)

    def publish_status(self, status):
        payload = {"drone_status": status, "drone_id": self.drone_id}
        if self.current_order_id is not None:
            payload["id"] = self.current_order_id       
        self.client.publish("server", json.dumps(payload))

    def notify_charging_station(self, action):
        payload = {"action": action, "drone_id": self.drone_id}
        if self.current_order_id is not None:
            payload["id"] = self.current_order_id
        self.client.publish("charging", json.dumps(payload))

    def start_sequence(self):
        print("start_sequence()")
        sense.show_message("Boot")
        self.play_sound("startup.mp3")
        self.stm.send('startup_complete')

    def start_charging(self):
        print("start_charging()")
        sense.clear(0, 255, 0) 
        self.publish_status("charging")
        self.start_animation('charging')
        self.notify_charging_station("drone_arriving")

    def end_charging(self):
        print("end_charging()")
        self.notify_charging_station("end_charging")
        self.stop_animation()

    def set_destination(self, dest):
        print(f"set_destination({dest})")

    def set_destination_for_departure(self):
        self.set_destination(self.departure_destination)

    def start_flying(self):
        print("start_flying()")
        self.start_animation('flying')
        sense.show_message("Flying...", text_colour=[0, 0, 255])
        self.play_sound("engine_hum.mp3")
        self.publish_status("in_flight")

    def send_location(self):
        print("send_location() - Updating Server")
        self.publish_status("location_update")

    def end_flight(self):
        print("end_flight()")
        self.stop_sound()
        self.stop_animation()

    def drop_off_food(self):
        print("drop_off_food()")
        sense.clear(255, 255, 0)
        self.publish_status("delivering")

    def food_dropped_off(self):
        print("food_dropped_off()")

    def arrived_pickup(self):
        print("arrived_pickup()")
        sense.show_message("Retrieve Food", text_colour=[255, 255, 255])
        self.publish_status("waiting_pickup")

    def hover(self):
        print("hover()")
        sense.show_message("Confirm Presence", text_colour=[0, 255, 255])
        self.publish_status("arrived")

    def secure_package(self):
        print("secure_package()")
        sense.clear(255, 165, 0)
        self.publish_status("aborting")

    def food_on_the_way(self):
        print("food_on_the_way()")

    def send_error(self):
        print("send_error()")
        sense.clear(255, 0, 0) 
        self.publish_status("error")

    def land(self):
        print("land() - Emergency landing")

    def show_stuck_warning(self):
        print("show_stuck_warning()")
        sense.clear(255, 0, 0) 
        self.publish_status("package_stuck")

    def start_shake_test(self):
        sense.clear(255, 0, 0) 
        threading.Thread(target=self._shake_test_loop, daemon=True).start()

    def _shake_test_loop(self):
            start_time = time.time()
            while time.time() - start_time < 15:
                accel = sense.get_accelerometer_raw()
                mag = (accel['x']**2 + accel['y']**2 + accel['z']**2)**0.5

                if mag > 2.0: 
                    print("Shake detected! Package unstuck.")
                    self.drop_off_food() 
                    return
                time.sleep(0.1)

            print("Shake timeout. Package is permanently stuck.")
            self.stm.send('package_stuck')
drone = Drone()

state_startup = {
    'name': 'Startup',
    'entry': 'start_sequence',
    'exit': 'set_destination("charging")'
}

state_charging = {
    'name': 'Charging',
    'entry': 'start_charging',
    'exit': 'end_charging; set_destination_for_departure'
}

state_in_flight = {
    'name': 'In_Flight',
    'entry': 'start_flying; start_timer("t", 30000)',
    't': 'send_location; start_timer("t", 30000)',
    'exit': 'end_flight; stop_timer("t")'
}

state_delivering = {
    'name': 'Delivering',
    'entry': 'drop_off_food',
    'exit': 'food_dropped_off; set_destination("charging")'
}

state_wait_pickup = {
    'name': 'Wait_Pickup',
    'entry': 'arrived_pickup',
    'exit': 'food_on_the_way; set_destination("delivery")' 
}

state_wait_presence = {
    'name': 'Wait_Presence',
    'entry': 'hover; start_timer("timeout", 30000)',
    'exit': 'stop_timer("timeout")'
}

state_abort_return = {
    'name': 'Abort_Return',
    'entry': 'secure_package',
    'exit': 'set_destination("charging")'
}

t0 = {'source': 'initial', 'target': 'Startup'}
t1 = {'trigger': 'startup_complete', 'source': 'Startup', 'target': 'In_Flight'}
t2 = {'trigger': 'order', 'source': 'Charging', 'target': 'In_Flight'}
t3 = {'trigger': 'at_dest_delivery', 'source': 'In_Flight', 'target': 'Wait_Presence'}
t4 = {'trigger': 'presence_confirmed', 'source': 'Wait_Presence', 'target': 'Delivering'}
t5 = {'trigger': 'delivered', 'source': 'Delivering', 'target': 'In_Flight'}
t6 = {'trigger': 'at_dest_pickup', 'source': 'In_Flight', 'target': 'Wait_Pickup'}
t7 = {'trigger': 'pickup_complete', 'source': 'Wait_Pickup', 'target': 'In_Flight'}
t8 = {'trigger': 'at_dest_charging', 'source': 'In_Flight', 'target': 'Charging'}
t9 = {'trigger': 'low_battery', 'source': 'In_Flight', 'target': 'Abort_Return'}
t10 = {'trigger': 'routed_to_station', 'source': 'Abort_Return', 'target': 'In_Flight'}
t11 = {'trigger': 'cancel', 'source': 'Wait_Presence', 'target': 'Abort_Return'}
t12 = {'trigger': 'timeout', 'source': 'Wait_Presence', 'target': 'Abort_Return'}
t13 = {'trigger': 'package_stuck', 'source': 'Delivering', 'target': 'Abort_Return'}

stm_drone = stmpy.Machine(
    name='stm_drone', 
    transitions=[
        t0, t1, t2, t3, t4, t5, t6, t7, t8,
        t9, t10, t11, t12, t13
    ], 
    states=[
        state_startup,
        state_charging,
        state_in_flight,
        state_wait_pickup,
        state_wait_presence,
        state_delivering,
        state_abort_return,
    ],
    obj=drone
)
drone.stm = stm_drone

driver = stmpy.Driver()
driver.add_machine(stm_drone)
driver.start()