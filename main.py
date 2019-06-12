# vim: set fileencoding=utf-8 expandtab shiftwidth=4 tabstop=4 softtabstop=4:

# Jacek Fedorynski <jfedor@jfedor.org>
# https://www.jfedor.org/

# I had to use a custom MicroPython build with an increased buffer size
# (-DRT_EXTRA in the Makefile) for HTTPS to work on an ESP8266.

import network
import machine
import time
import binascii
import json
import collections
import struct
import urequests

TOGGL_API_TOKEN='<put your API token here>'

PROJECT_IDS = [
    151554235,
    151554237,
    151554248,
    151554255,
    151554261,
]

ATTINY_SIGNAL_PIN = 0 # D3 is GPIO0
SCL_PIN = 14 # D5 is GPIO14
SDA_PIN = 12 # D6 is GPIO12

SensorData = collections.namedtuple('SensorData', [ 'accel_x', 'accel_y', 'accel_z', 'temperature', 'gyro_x', 'gyro_y', 'gyro_z' ])

def get_stable_orientation(valid_orientations):
    i2c = machine.I2C(scl=machine.Pin(SCL_PIN), sda=machine.Pin(SDA_PIN))
    mpu6050_init(i2c)
    history = []
    while True:
        sensor_data = mpu6050_get_data(i2c)
        accel_values = (sensor_data.accel_x, sensor_data.accel_y, sensor_data.accel_z)
        if accel_values != (0, 0, 0):
            history.append(accel_values)
            history = history[-10:]
            motion = sum(variance([x[j] for x in history]) for j in range(3))
            print(motion)
            orientation = tuple(threshold(x) for x in history[-1])
            if motion < 500000 and len(history) == 10 and orientation in valid_orientations:
                break
        time.sleep(0.1)
    return orientation

def mpu6050_init(i2c):
    i2c.start()
    i2c.writeto(0x68, bytearray([0x6B, 0]))
    i2c.stop()

def mpu6050_get_data(i2c):
    i2c.start()
    raw_bytes = i2c.readfrom_mem(0x68, 0x3B, 14)
    i2c.stop()
    return SensorData(*struct.unpack('>hhhhhhh', raw_bytes))

def variance(values):
    mean = sum(values) / len(values)
    return sum((x-mean)**2 for x in values)

def threshold(x):
    if x > 12000:
        return 1
    if x < -12000:
        return -1
    if x > -2000 and x < 2000:
        return 0
    return None

def wait_for_wifi():
    sta_if = network.WLAN(network.STA_IF)
    while not sta_if.isconnected():
        print('waiting for wifi to connect...')
        time.sleep(1)
    print('connected!')

def stop_time_entry():
    auth_header_ = auth_header()
    resp = urequests.request('GET', 'https://www.toggl.com/api/v8/time_entries/current', headers=auth_header_)
    print(resp.content)
    data = json.loads(resp.content)['data']
    if data:
        time_entry_id = data['id']
        headers = { 'Content-length': '0' }
        headers.update(auth_header_)
        resp = urequests.request('PUT', 'https://www.toggl.com/api/v8/time_entries/{}/stop'.format(time_entry_id), headers=headers)
        print(resp.content)

def start_time_entry(time_entry_id):
    post_data = {
        "time_entry": {
            "pid": time_entry_id,
            "created_with": "TimeCube"
        }
    }
    resp = urequests.request('POST', 'https://www.toggl.com/api/v8/time_entries/start', json=post_data, headers=auth_header())
    print(resp.content)

def auth_header():
    return { 'Authorization': 'Basic ' + binascii.b2a_base64(TOGGL_API_TOKEN+':api_token')[:-1].decode('ascii') }


valid_orientations = {
    (0,  0,  1): stop_time_entry,
    (1,  0,  0): lambda: start_time_entry(PROJECT_IDS[0]),
    (0,  1,  0): lambda: start_time_entry(PROJECT_IDS[1]),
    (-1, 0,  0): lambda: start_time_entry(PROJECT_IDS[2]),
    (0, -1,  0): lambda: start_time_entry(PROJECT_IDS[3]),
    (0,  0, -1): lambda: start_time_entry(PROJECT_IDS[4]),
}

pin = machine.Pin(ATTINY_SIGNAL_PIN, machine.Pin.OUT)

pin.value(0)

orientation = get_stable_orientation(valid_orientations)
print(orientation)

wait_for_wifi()

valid_orientations[orientation]()

pin.value(1)
