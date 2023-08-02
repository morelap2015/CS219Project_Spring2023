#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

import network
import socket
import machine
import ujson
import uhashlib
import ubinascii
import gc
import pycom
import os
import machine
import time
import ubinascii
from network import LoRa, WLAN

# Try to get version number
try:
    from OTA_VERSION import VERSION
except ImportError:
    VERSION = '1.0.0'


class OTA():
    # The following two methods need to be implemented in a subclass for the
    # specific transport mechanism e.g. WiFi

    def connect(self):
        raise NotImplementedError()

    def get_data(self, req, dest_path=None, hash=False):
        raise NotImplementedError()

    # OTA methods

    def get_current_version(self):
        return VERSION

    def get_update_manifest(self):
        req = "manifest.json?current_ver={}".format(self.get_current_version())
        manifest_data = self.get_data(req).decode()
        manifest = ujson.loads(manifest_data)
        gc.collect()
        return manifest

    def update(self):
        manifest = self.get_update_manifest()
        if manifest is None:
            print("Already on the latest version")
            return

        # Download new files and verify hashes
        for f in manifest['new'] + manifest['update']:
            # Upto 5 retries
            for _ in range(5):
                try:
                    self.get_file(f)
                    break
                except Exception as e:
                    print(e)
                    msg = "Error downloading `{}` retrying..."
                    print(msg.format(f['URL']))
            else:
                raise Exception("Failed to download `{}`".format(f['URL']))

        # Backup old files
        # only once all files have been successfully downloaded
        for f in manifest['update']:
            self.backup_file(f)

        # Rename new files to proper name
        for f in manifest['new'] + manifest['update']:
            new_path = "{}.new".format(f['dst_path'])
            dest_path = "{}".format(f['dst_path'])

            os.rename(new_path, dest_path)

        # `Delete` files no longer required
        # This actually makes a backup of the files incase we need to roll back
        for f in manifest['delete']:
            self.delete_file(f)

        # Flash firmware
        if "firmware" in manifest:
            self.write_firmware(manifest['firmware'])

        # Save version number
        try:
            self.backup_file({"dst_path": "/flash/OTA_VERSION.py"})
        except OSError:
            pass  # There isnt a previous file to backup
        with open("/flash/OTA_VERSION.py", 'w') as fp:
            fp.write("VERSION = '{}'".format(manifest['version']))
        from OTA_VERSION import VERSION

        # Reboot the device to run the new decode
        machine.reset()

    def get_file(self, f):
        new_path = "{}.new".format(f['dst_path'])

        # If a .new file exists from a previously failed update delete it
        try:
            os.remove(new_path)
        except OSError:
            pass  # The file didnt exist

        # Download new file with a .new extension to not overwrite the existing
        # file until the hash is verified.
        hash = self.get_data(f['URL'].split("/", 3)[-1],
                             dest_path=new_path,
                             hash=True)

        # Hash mismatch
        if hash != f['hash']:
            print(hash, f['hash'])
            msg = "Downloaded file's hash does not match expected hash"
            raise Exception(msg)

    def backup_file(self, f):
        bak_path = "{}.bak".format(f['dst_path'])
        dest_path = "{}".format(f['dst_path'])

        # Delete previous backup if it exists
        try:
            os.remove(bak_path)
        except OSError:
            pass  # There isnt a previous backup

        # Backup current file
        os.rename(dest_path, bak_path)

    def delete_file(self, f):
        bak_path = "/{}.bak_del".format(f)
        dest_path = "/{}".format(f)

        # Delete previous delete backup if it exists
        try:
            os.remove(bak_path)
        except OSError:
            pass  # There isnt a previous delete backup

        # Backup current file
        os.rename(dest_path, bak_path)

    def write_firmware(self, f):
        hash = self.get_data(f['URL'].split("/", 3)[-1],
                             hash=True,
                             firmware=True)
        # TODO: Add verification when released in future firmware


class WiFiOTA(OTA):
    def __init__(self, ssid, password, ip, port):
        self.SSID = ssid
        self.password = password
        self.ip = ip
        self.port = port

    def connect(self):
        self.wlan = network.WLAN(mode=network.WLAN.STA)
        if not self.wlan.isconnected() or self.wlan.ssid() != self.SSID:
            for net in self.wlan.scan():
                if net.ssid == self.SSID:
                    self.wlan.connect(self.SSID, auth=(network.WLAN.WPA2,
                                                       self.password))
                    while not self.wlan.isconnected():
                        machine.idle()  # save power while waiting
                    break
            else:
                raise Exception("Cannot find network '{}'".format(SSID))
        else:
            # Already connected to the correct WiFi
            pass

    def _http_get(self, path, host):
        req_fmt = 'GET /{} HTTP/1.0\r\nHost: {}\r\n\r\n'
        req = bytes(req_fmt.format(path, host), 'utf8')
        return req

    def get_data(self, req, dest_path=None, hash=False, firmware=False):
        h = None

        # Connect to server
        print("Requesting: {}".format(req))
        s = socket.socket(socket.AF_INET,
                          socket.SOCK_STREAM,
                          socket.IPPROTO_TCP)
        s.connect((self.ip, self.port))

        # Request File
        s.sendall(self._http_get(req, "{}:{}".format(self.ip, self.port)))

        try:
            content = bytearray()
            fp = None
            if dest_path is not None:
                if firmware:
                    raise Exception("Cannot write firmware to a file")
                fp = open(dest_path, 'wb')

            if firmware:
                pycom.ota_start()

            h = uhashlib.sha1()

            # Get data from server
            result = s.recv(100)

            start_writing = False
            while (len(result) > 0):
                # Ignore the HTTP headers
                if not start_writing:
                    if "\r\n\r\n" in result:
                        start_writing = True
                        result = result.decode().split("\r\n\r\n")[1].encode()

                if start_writing:
                    if firmware:
                        pycom.ota_write(result)
                    elif fp is None:
                        content.extend(result)
                    else:
                        fp.write(result)

                    if hash:
                        h.update(result)

                result = s.recv(100)

            s.close()

            if fp is not None:
                fp.close()
            if firmware:
                pycom.ota_finish()

        except Exception as e:
            # Since only one hash operation is allowed at Once
            # ensure we close it if there is an error
            if h is not None:
                h.digest()
            raise e

        hash_val = ubinascii.hexlify(h.digest()).decode()

        if dest_path is None:
            if hash:
                return (bytes(content), hash_val)
            else:
                return bytes(content)
        elif hash:
            return hash_val

# TODO switch implementation form WiFiOTA to LoRaOTA
class LoRaOTA(OTA):
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

    def init(self, process_msg_callback):
        self._process_ota_msg = process_msg_callback

    def connect(self, lora=None):
        if lora is None:
            self.lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)
        else:
            self.lora = lora

        # Uncomment for US915 / AU915 & Pygate
        for i in range(0, 8):
            self.lora.remove_channel(i)
        for i in range(16, 65):
            self.lora.remove_channel(i)
        for i in range(66, 72):
            self.lora.remove_channel(i)

        if not self.lora.has_joined():
            self.lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)
            while not lora.has_joined():
                time.sleep(2.5)
                print('Not yet joined...')
        else:
            # Already connected to LoRa
            pass
    

    def has_joined(self):
        return self.lora.has_joined()

    def _create_socket(self):

        # create a LoRa socket
        self.sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

        # set the LoRaWAN data rate
        self.sock.setsockopt(socket.SOL_LORA, socket.SO_DR, self.dr)

        # make the socket non blocking
        self.sock.setblocking(False)

        time.sleep(2)

    def send(self, packet):
        with self.s_lock:
            self.sock.send(packet)

    def receive(self, bufsize):
        with self.q_lock:
            if len(self._msg_queue) > 0:
                return self._msg_queue.pop(0)
        return ''

    def get_dev_eui(self):
        return binascii.hexlify(self.lora.mac()).decode('ascii')
    
    def receive_callback(self, lora):
        events = lora.events()
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

    def _http_get(self, path, host):
        req_fmt = 'GET /{} HTTP/1.0\r\nHost: {}\r\n\r\n'
        req = bytes(req_fmt.format(path, host), 'utf8')
        return req

    def get_data(self, req, dest_path=None, hash=False, firmware=False):
        h = None

        # Connect to server
        print("Requesting: {}".format(req))
        s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        s.connect((self.ip, self.port))

        # Request File
        s.sendall(self._http_get(req, "{}:{}".format(self.ip, self.port)))

        try:
            content = bytearray()
            fp = None
            if dest_path is not None:
                if firmware:
                    raise Exception("Cannot write firmware to a file")
                fp = open(dest_path, 'wb')

            if firmware:
                pycom.ota_start()

            h = uhashlib.sha1()

            # Get data from server
            result = s.recv(100)

            start_writing = False
            while (len(result) > 0):
                # Ignore the HTTP headers
                if not start_writing:
                    if "\r\n\r\n" in result:
                        start_writing = True
                        result = result.decode().split("\r\n\r\n")[1].encode()

                if start_writing:
                    if firmware:
                        pycom.ota_write(result)
                    elif fp is None:
                        content.extend(result)
                    else:
                        fp.write(result)

                    if hash:
                        h.update(result)

                result = s.recv(100)

            s.close()

            if fp is not None:
                fp.close()
            if firmware:
                pycom.ota_finish()

        except Exception as e:
            # Since only one hash operation is allowed at Once
            # ensure we close it if there is an error
            if h is not None:
                h.digest()
            raise e

        hash_val = ubinascii.hexlify(h.digest()).decode()

        if dest_path is None:
            if hash:
                return (bytes(content), hash_val)
            else:
                return bytes(content)
        elif hash:
            return hash_val