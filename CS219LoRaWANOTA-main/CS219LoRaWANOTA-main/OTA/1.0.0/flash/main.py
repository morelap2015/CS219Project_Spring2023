#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from network import LoRa, WLAN
import socket
import time
from OTA import WiFiOTA
from time import sleep
import pycom
import binascii
import ubinascii

# # Turn on GREEN LED
# pycom.heartbeat(False)
# pycom.rgbled(0xff00)


# Initialize LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.US915)

# Tan's Tenant
app_eui = ubinascii.unhexlify('58A0CBFFFE803F9C')
app_key = ubinascii.unhexlify('E82511CC86A1FF6F8AEC6238920225DA')
dev_eui = ubinascii.unhexlify('70B3D5499A2B29C2')

# Mark's Tenant
# app_eui = ubinascii.unhexlify('0102030405060708')
# app_key = ubinascii.unhexlify('66C384977A646B8BF820D5EF83487397')
# dev_eui = ubinascii.unhexlify('70B3D5499A2B29C2')


# Uncomment for US915 / AU915 & Pygate
for i in range(0, 8):
    lora.remove_channel(i)
for i in range(16, 65):
    lora.remove_channel(i)
for i in range(66, 72):
    lora.remove_channel(i)


# join a network using OTAA (Over the Air Activation)
lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    time.sleep(2.5)
    print('Not yet joined...')

print('Joined')

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

print("Socket Created")

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 3)
print("Set Socket Data Rate")

# make the socket blocking
# (waits for the data to be sent and for the 2 receive windows to expire)
s.setblocking(True)
print("Set Socket Blocking")

# creat a object to hold firmware files
# data = []

flag = True
# s.send(bytes([0x01, 0x02, 0x03]))
s.settimeout(10.0) # configure a timeout value of 3 seconds
try:
    s.send(bytes([0x03, 0x02, 0x01]))
    print("Sending First 3, 2, 1")
    num_seg = s.recv(64)
    num_seg = int.from_bytes(num_seg, "big")
    print("Received num_seg is {}".format(num_seg))
    s.settimeout(10.0)
except socket.timeout:
    print("Socket Timed Out, manual retranmission to get num_seg")
    s.send(bytes([0x01, 0x02, 0x03]))
    print("Sending First 3, 2, 1")
    num_seg = s.recv(64)
    num_seg = int.from_bytes(num_seg, "big")
    print("Received num_seg is {}".format(num_seg))

# s.send(bytes([0x03, 0x02, 0x01]))
# print("Sending Second 3, 2, 1")
# rx_pkt = s.recv(64)
# print("Received rx_pkt is {}".format(rx_pkt))

start_time = time.time()
data = [None] * num_seg

receiving_failed=False
i = 0

while i < (num_seg): # check bounds, I think this should be num_seg
    # i+=1
    try:
        if(receiving_failed):
            s.send(bytes([0x01, 0x02, 0x03]))
        else:
            s.send(bytes([0x03, 0x02, 0x01]))
        print("Sending {} iter: 3, 2, 1".format(i))
        rx_pkt = s.recv(64)
        receiving_failed = False
        # data.append(rx_pkt)
        # print("data was techncally received...")
        # print("The value of i is {} and data[i] is {}".format(i, data[i]))
        data[i]=rx_pkt
        # print("UPDATED MEMORY")
        print("The value of i is {} and data[i] is {}".format(i, data[i]))
        print("Received rx_pkt for iter {} is {}".format(i, rx_pkt))
        i+=1
    except socket.timeout:
        print("Socket Timed Out, retransmitting for iteration {}".format(i))
        # i-=1 # Need to check if this is a proper way to edit iterator in for loop, it may not be...
        # print("New value of i is {}".format(i))
        receiving_failed = True
        # print('No packet received')
        # s.send(bytes([0x01, 0x02, 0x03]))
        # print("Sending {} iter: 3, 2, 1".format(i))
        # rx_pkt = s.recv(64)
        # print("Received rx_pkt is {}".format(rx_pkt))


    # s.send(bytes([0x03, 0x02, 0x01]))
    # print("Sending {} iter: 3, 2, 1".format(i))
    # rx_pkt = s.recv(64)
    # data.append(rx_pkt)
    # print("Received rx_pkt is {}".format(rx_pkt))

end_time_1 = time.time()
print("Time to move file over LoRa was: {} seconds".format(end_time_1-start_time))
# Write 2d binary array data to a file

# ota.bin 
with open('/flash/ota_2.bin', 'wb') as f:
    for i in range(len(data)):
        f.write(data[i])
end_time_2 = time.time()

print("Time to Flash Firmware was {} seconds".format(end_time_2-end_time_1))
print("Time for Entire Process was  {} seconds".format(end_time_2-start_time))

