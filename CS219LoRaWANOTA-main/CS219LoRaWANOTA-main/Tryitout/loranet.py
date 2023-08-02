#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from network import LoRa
import socket
import binascii
import ubinascii
import struct
import time
import _thread

class LoraNet:
    def __init__(self, frequency, dr, region, device_class=LoRa.CLASS_C, activation = LoRa.OTAA, auth = None):
        self.frequency = frequency
        self.dr = dr
        self.region = region
        self.device_class = device_class
        self.activation = activation
        self.auth = auth
        self.sock = None
        self._exit = False
        self.s_lock = _thread.allocate_lock()
        self.lora = LoRa(mode=LoRa.LORAWAN, region = self.region, device_class = self.device_class)

        self._msg_queue = []
        self.q_lock = _thread.allocate_lock()
        self._process_ota_msg = None

    def stop(self):
        self._exit = True

    def init(self, process_msg_callback):
        self._process_ota_msg = process_msg_callback

    def receive_callback(self, lora):
        print("Im in receive_callback")
        events = lora.events()
        print("RECEIVE_CALLBACK TRIGGERED!!! {}".format(LoRa.RX_PACKET_EVENT))
        if events & LoRa.RX_PACKET_EVENT:
            rx, port = self.sock.recvfrom(256)
            if rx:
                if '$OTA' in rx:
                    print("OTA msg received: {}".format(rx))
                    self._process_ota_msg(rx.decode())
                else:
                    self.q_lock.acquire()
                    self._msg_queue.append(rx)
                    self.q_lock.release()

    def transmit_callback(self, lora):
        print("Im in transmit_callback")
        events = lora.events()
        print("TRANSMIT_CALLBACK TRIGGERED!!! {}".format(LoRa.TX_PACKET_EVENT))
        if events & LoRa.TX_PACKET_EVENT:
            print('Packet sent')
            self.s_lock.release()

    def connect(self):
        if self.activation != LoRa.OTAA and self.activation != LoRa.ABP:
            raise ValueError("Invalid Lora activation method")
        if len(self.auth) < 3:
            raise ValueError("Invalid authentication parameters")

        self.lora.callback(trigger=LoRa.RX_PACKET_EVENT, handler=self.receive_callback)
        self.lora.callback(trigger=LoRa.TX_PACKET_EVENT, handler=self.transmit_callback)

        # set the 3 default channels to the same frequency
        # self.lora.add_channel(0, frequency=self.frequency, dr_min=0, dr_max=5)
        # self.lora.add_channel(1, frequency=self.frequency, dr_min=0, dr_max=5)
        # self.lora.add_channel(2, frequency=self.frequency, dr_min=0, dr_max=5)

        # remove all the non-default channels
        # for i in range(3, 16):
        #     self.lora.remove_channel(i)
        # Uncomment for US915 / AU915 & Pygate
        for i in range(0, 8):
            self.lora.remove_channel(i)
        for i in range(16, 65):
            self.lora.remove_channel(i)
        for i in range(66, 72):
            self.lora.remove_channel(i)

        # authenticate with abp or ota
        if self.activation == LoRa.OTAA:
            self._authenticate_otaa(self.auth)
        else:
            self._authenticate_abp(self.auth)

        # create socket to server
        self._create_socket()

    def _authenticate_otaa(self, auth_params):

        # create an OTAA authentication params
        self.app_eui = ubinascii.unhexlify('58A0CBFFFE803F9C')
        self.app_key = ubinascii.unhexlify('E82511CC86A1FF6F8AEC6238920225DA')
        self.dev_eui = ubinascii.unhexlify('70B3D5499A2B29C2')

        #self.lora.join(activation=LoRa.OTAA, auth=(self.dev_eui, self.app_eui, self.app_key), timeout=0, dr=self.dr)
        self.lora.join(activation=LoRa.OTAA, auth=(self.dev_eui, self.app_eui, self.app_key), timeout=0)
        while not self.lora.has_joined():
            time.sleep(2.5)
            print('Not joined yet...')
        print("Joined!")

    def has_joined(self):
        return self.lora.has_joined()

    def _authenticate_abp(self, auth_params):
        # create an ABP authentication params
        self.dev_addr = struct.unpack(">l", binascii.unhexlify(auth_params[0]))[0]
        self.nwk_swkey = binascii.unhexlify(auth_params[1])
        self.app_swkey = binascii.unhexlify(auth_params[2])

        self.lora.join(activation=LoRa.ABP, auth=(self.dev_addr, self.nwk_swkey, self.app_swkey))

    def _create_socket(self):

        # create a LoRa socket
        self.sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

        # set the LoRaWAN data rate
        self.sock.setsockopt(socket.SOL_LORA, socket.SO_DR, self.dr)

        # make the socket non blocking
        self.sock.setblocking(False)
        print("In create socket {}".format(self.lora.RX_PACKET_EVENT))
        print("Create Socket, Self Message Queue: {}".format(self._msg_queue))
        time.sleep(2)

    def send(self, packet):
        with self.s_lock:
            self.sock.send(packet)

    def receive(self, bufsize):
        with self.q_lock:
            print("Self Message Queue: {}".format(self._msg_queue))
            if len(self._msg_queue) > 0:
                return self._msg_queue.pop(0)
        return 'Empty String'

    def get_dev_eui(self):
        return binascii.hexlify(self.lora.mac()).decode('ascii')

    def change_to_multicast_mode(self, mcAuth):
        print('Start listening for firmware updates ...........')

        if self.device_class != LoRa.CLASS_C:
            self.lora = LoRa(mode=LoRa.LORAWAN, region = self.region, device_class=LoRa.CLASS_C)
            self.connect()

        mcAddr = struct.unpack(">l", binascii.unhexlify(mcAuth[0]))[0]
        mcNwkKey = binascii.unhexlify(mcAuth[1])
        mcAppKey = binascii.unhexlify(mcAuth[2])

        self.lora.join_multicast_group(mcAddr, mcNwkKey, mcAppKey)