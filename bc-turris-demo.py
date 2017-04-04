#!/usr/bin/env python3
# [UNIXový čas, přijaté bajty, přijaté pakety, odeslané bajty, odeslané pakety]

import os
import sys
import json
import time
import paho.mqtt.client as mqtt
import fcntl
import subprocess
from datetime import datetime
import base64

MAX_DL = 10 * 1024 * 1024 #10MB/s


def sizeof_fmt(num, suffix='B/s'):
    num /= 1024.0

    for unit in ['k','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def mqtt_on_connect(client, userdata, flags, rc):
    client.subscribe('nodes/+/+/+')


def mqtt_on_message(client, userdata, msg):
    
    print(msg.topic,  msg.payload.decode())

    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        return

    if "nodes/base/thermometer/i2c0-49" == msg.topic:
        userdata['base']['temperature'] = payload['temperature'][0]
    elif "nodes/base/humidity-sensor/i2c0-5f" == msg.topic:
        userdata['base']['relative-humidity'] = payload['relative-humidity'][0]
    elif "nodes/base/lux-meter/i2c0-44" == msg.topic:
        userdata['base']['illuminance'] = payload['illuminance'][0]

    elif "nodes/remote/thermometer/i2c0-48" == msg.topic:
        userdata['remote']['temperature'] = payload['temperature'][0]
    elif "nodes/remote/humidity-sensor/i2c0-40" == msg.topic:
        userdata['remote']['relative-humidity'] = payload['relative-humidity'][0]
    elif "nodes/remote/lux-meter/i2c0-44" == msg.topic:
        userdata['remote']['illuminance'] = payload['illuminance'][0]
    elif "nodes/remote/barometer/i2c0-60" == msg.topic:
        userdata['remote']['pressure'] = payload['pressure'][0]

def run():

    userdata={'remote': {"temperature": None, 'relative-humidity': None, 'illuminance': None, 'pressure' : None}, 
    'base': {"temperature": None, 'relative-humidity': None, 'illuminance': None, 'pressure' : None}}

    show = 4
    node = 'remote'

    client = mqtt.Client(userdata = userdata)
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    client.connect('localhost', 1883, keepalive=10)
    client.loop_start()

    pixels = [0] * 144 * 4

    max_pixel_last = 0

    last_data = None
    while True:
        p = subprocess.Popen(["luci-bwc", "-i", "eth1"], stdout=subprocess.PIPE)
        p.wait()
        try:
            data = p.stdout.read().decode().split('\n')[-2]
        except Exception as e:
            data = None
        p.stdout.close()
        if data:
            data = json.loads(data)
            print(data)

            if last_data and last_data != data:
                dnload = sizeof_fmt(data[1]-last_data[1])
                upload = sizeof_fmt(data[3]-last_data[3])
                print('dnload', dnload)
                print('upload', upload)
     
                client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 5, "text": datetime.now().strftime('%y/%m/%d %H:%M:%S') + "      " }), qos=1)

                client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 25, "text": "D/L: "+(dnload.rjust(7)) + "       " }), qos=1)
                client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 45, "text": "U/L: "+(upload.rjust(7)) + "       " }), qos=1)

                max_pixel = round((data[1]-last_data[1]) * (144.0 / MAX_DL)) * 4

                print('max_pixel', max_pixel)

                if max_pixel_last != max_pixel:
                    max_pixel_last = max_pixel

                    for i in range(0, 144 * 4, 4):
                        if i < max_pixel:
                            pixels[i] = 0x40
                        else:
                            pixels[i] = 0x00

                    client.publish('nodes/base/led-strip/-/set', json.dumps({'pixels': base64.b64encode(bytearray(pixels)).decode()}))
 
            last_data = data

        if show == 4 :
            node = 'remote' if node == 'base' else 'base'
            show = 0
            client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 65, "text": "node/" + node + "     "}))

        if show == 0 :
            value = "%.2f C" % userdata[node]['temperature'] if userdata[node]['temperature'] is not None else ''
            client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 85, "text": value + "                 "}))

            value = "%.2f %%" % userdata[node]['relative-humidity'] if userdata[node]['relative-humidity'] is not None else ''
            print(value)
            client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 105, "text": value + "                "}))
        
        elif show == 2:

            value = "%.2f lux" % userdata[node]['illuminance'] if userdata[node]['illuminance'] is not None else ''
            client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 85, "text": value + "                 " }))

            value = "%.2f KPa" % (userdata[node]['pressure'] / 1000.0) if userdata[node]['pressure'] is not None else ''
            client.publish("nodes/base/display/text/set", json.dumps({"x": 5, "y": 105, "text": value + "                "}))


        time.sleep(1)
        show += 1

def loop():
    run()
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(e)
        if os.getenv('DEBUG', False):
            raise e

def main():
    loop()
    while True:
        loop()
        time.sleep(3)

if __name__ == '__main__':
    main()
