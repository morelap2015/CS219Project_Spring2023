from network import LoRa
import pycom
import socket
import time
import ubinascii
# NNSXS.SUBWFSYB26D6F7YRGRXRGTH7ZQLYEVEM4TKCGKQ.GRL4INLDTEMVMTCVVXVHMAY3JWFWWCI4TGM5MFEZJR3SQKJ3K7HQ
# ^API key
# Initialise LoRa in LORAWAN mode.
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.US915)

# create an OTAA authentication parameters, change them to the provided credentials
# app_eui = ubinascii.unhexlify('ADA4DAE3AC12676B')
app_eui = ubinascii.unhexlify('58A0CBFFFE803F9C')
app_key = ubinascii.unhexlify('E82511CC86A1FF6F8AEC6238920225DA')

# app_key = ubinascii.unhexlify('11B0282A189B75B0B4D2D8C7FA38548B')
#app_key = ubinascii.unhexlify('QYNVIPCESUULZ73YK2CGM2KRBGSTIGVJXCZMRSY')
#uncomment to use LoRaWAN application provided dev_eui
# dev_eui = ubinascii.unhexlify('70B3D549938EA1EE')
dev_eui = ubinascii.unhexlify('70B3D5499A2B29C2')

# Uncomment for US915 / AU915 & Pygate
for i in range(0,8):
    lora.remove_channel(i)
for i in range(16,65):
    lora.remove_channel(i)
for i in range(66,72):
    lora.remove_channel(i)

# join a network using OTAA (Over the Air Activation)
#uncomment below to use LoRaWAN application provided dev_eui
#lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)
lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    time.sleep(2.5)
    print('Not yet joined...')

print('Joined')
# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
print("Socket Created")
# set the LoRaWAN data rate
# set the LoRaWAN data rate - need to set to "3" for USA
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 3)
print("Set Socket Data Rate")

# make the socket blocking
# (waits for the data to be sent and for the 2 receive windows to expire)
s.setblocking(True)
print("Set Socket Blocking")

# send some data
s.send(bytes([0x01, 0x02, 0x03]))
print("Sent data")
# make the socket non-blocking
# (because if there's no data received it will block forever...)
s.setblocking(False)

# get any data received (if any...)
data = s.recv(64)
print(data)