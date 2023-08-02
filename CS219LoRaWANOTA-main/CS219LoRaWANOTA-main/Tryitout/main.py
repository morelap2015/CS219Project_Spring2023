from network import LoRa, WLAN
import socket
import time
from time import sleep
import pycom
import ubinascii
from OTA import WiFiOTA
import uos

from config import WIFI_SSID, WIFI_PW, SERVER_IP

pycom.heartbeat(True)

# Setup OTA
ota = WiFiOTA(WIFI_SSID,
              WIFI_PW,
              SERVER_IP,  # Update server address
              8000)  # Update server port

# Turn off WiFi to save power
w = WLAN()
w.deinit()

# Initialise LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.US915)

# app_eui = ubinascii.unhexlify('70B3D57ED0008CD6')
app_eui = ubinascii.unhexlify('58A0CBFFFE803F9C')
# Need to change the app_key
#app_key = ubinascii.unhexlify('B57F36D88691CEC5EE8659320169A61C')
app_key = ubinascii.unhexlify('E82511CC86A1FF6F8AEC6238920225DA')
dev_eui = ubinascii.unhexlify('70B3D5499A2B29C2')
# Get device version information
version_info = uos.uname()

# print("VERSION INFO {}".format(version_info))
# print(type(version_info))
# From device version, get firmware version number
release_info = version_info[2]
print(release_info)
# Uncomment for US915 / AU915 & Pygate
for i in range(0,8):
    lora.remove_channel(i)
for i in range(16,65):
    lora.remove_channel(i)
for i in range(66,72):
    lora.remove_channel(i)

# join a network using OTAA (Over the Air Activation)
lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    time.sleep(2.5)
    print('Not yet joined...')
print("joined!")
# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
print("Socket created!")
# set the LoRaWAN data rate - need to set to 3 for USA
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 3)
print("Data Rate Set!")
# make the socket blocking
# (waits for the data to be sent and for the 2 receive windows to expire)
s.setblocking(False)
print("Blocking NOT Set!")

while True: ##### DO NOT NEED OUTER WHILE LOOP, NO CONTINUOUS RETRANSMISSION NECESSARY #####
    # send some data
    s.send(bytes([0x04, 0x05, 0x06]))

    # make the socket non-blocking
    # (because if there's no data received it will block forever...)
    s.setblocking(False)
    s.settimeout(3.0) # configure a timeout value of 3 seconds
    try:
        rx_pkt = s.recv(64)   # get the packet received (if any)
        print(rx_pkt)
    except socket.timeout:
        print('No packet received')
    # # get any data received (if any...)
    # data = s.recv(64)
    # print ("DATA RECEIVED")
    # # Some sort of OTA trigger
    # # data = bytes([0x01, 0x02, 0x03])
    # print("Hardcoded Trigger -> should start OTA")
    # if data == bytes([0x01, 0x02, 0x03]):
    #     print("Performing OTA")
    #     # Perform OTA
    #     ota.connect()
    #     ota.update()

    sleep(5)

# #!/usr/bin/env python
# #
# # Copyright (c) 2019, Pycom Limited.
# #
# # This software is licensed under the GNU GPL version 3 or any
# # later version, with permitted additional terms. For more information
# # see the Pycom Licence v1.0 document supplied with this file, or
# # available at https://www.pycom.io/opensource/licensing
# #

# from loranet import LoraNet
# from ota import LoraOTA
# from network import LoRa
# import machine
# import utime

# def main():
#     # LORA_FREQUENCY = 868100000
#     LORA_FREQUENCY = 910000000
#     LORA_NODE_DR = 3 # DR has to be 3 for USA
#     LORA_REGION = LoRa.US915
#     LORA_DEVICE_CLASS = LoRa.CLASS_C
#     LORA_ACTIVATION = LoRa.OTAA
#     LORA_CRED = ('240ac4fffe0bf998', '948c87eff87f04508f64661220f71e3f', '5e6795a5c9abba017d05a2ffef6ba858')

#     lora = LoraNet(LORA_FREQUENCY, LORA_NODE_DR, LORA_REGION, LORA_DEVICE_CLASS, LORA_ACTIVATION, LORA_CRED)
#     lora.connect()

#     print("LoRa fire up")
#     ota = LoraOTA(lora)
#     print("LoRa fired up!")

#     while True:
#         print("in main.py: {}".format(LoRa.RX_PACKET_EVENT))
#         rx = lora.receive(256)
#         if rx:
#             print('Received user message: {}'.format(rx))
#         else:
#             print("No message received")

#         utime.sleep(2)

# main()

# #try:
# #    main()
# #except Exception as e:
# #    print('Firmware exception: Reverting to old firmware')
# #    LoraOTA.revert()