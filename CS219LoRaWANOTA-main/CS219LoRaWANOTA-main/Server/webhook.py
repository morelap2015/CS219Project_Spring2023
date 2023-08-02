from flask import Flask, request 
import requests
import json
import base64
import get_blobs
from datetime import datetime

app = Flask(__name__)

# our tenant
push_url = 'https://lorala.nam1.cloud.thethings.industries/api/v3/as/applications/my-application/webhooks/test-webhook/devices/eui-70b3d5499a2b29c2/down/push'
replace_url = 'https://lorala.nam1.cloud.thethings.industries/api/v3/as/applications/my-application/webhooks/test-webhook/devices/eui-70b3d5499a2b29c2/down/replace'
headers = {'Authorization': "Bearer NNSXS.36NKRJCT6PUYWDZJR3B26XRA5FAY4BQSN2SMSVI.DB5MRJ2YQBOXNSAGU5LKMG6RDMEBOVD3SEDHXAENTO7V2UKFTHEQ",
       'Content-Type': "application/json",
       'User-Agent': "my-integration/my-integration-version"}
replace_data = {
    "downlinks":[{
       "f_port":2,
       "frm_payload": "EQ==",
    }]
  }

# Mike's tenant
# url = 'https://219proj.nam1.cloud.thethings.industries/api/v3/as/applications/my-application/webhooks/test-webhook/devices/eui-70b3d5499a2b29c2/down/push'
# headers = {'Authorization': "Bearer NNSXS.7WS6FXL64X66VEW5MCGPMR5NZ65BYVUDZ7P4NKI.4RFGQD4GRGPOGETGBEXPDX3XTRYUYS4UQAIEGYBDEXALCJTJOY5A",
#        'Content-Type': "application/json",
#        'User-Agent': "my-integration/my-integration-version"}
# data = {"downlinks":[{
#        "f_port":2,
#        "frm_payload": "EQ==",
#     }]
#   }

file_chunks = []
last_sent = None
blob = None

@app.route('/')
def hello():
    return "Hello World!"


@app.route('/join-accept', methods=['POST'])
def webhook3():
    print("join-accept")

    # clear any blobs in the buffer
    file_chunks.clear()

    # prepare the blobs for OTA
    file_chunks.extend(get_blobs.get_blobs_from_file('first100kb_ota.bin'))
    length = len(file_chunks)
    file_chunks.insert(0, length.to_bytes((length.bit_length() + 7 )// 8, 'big'))
    print(file_chunks)

    print(f"Chunks length: {length}")
    log('application', f"Chunks length: {len(file_chunks)}")
    
    if(request.method == 'POST'):
        print(request.json)
        log("join-accept", request.json)
        log("Time", "NEW TEST RUNNING!!!!!!")
        log("Time", datetime.now().isoformat())

        res = requests.post(replace_url, headers=headers)
        return 'success', 200

    return 'success', 200

@app.route('/uplinks', methods=['POST'])
def webhook1():
    global file_chunks
    global last_sent
    global blob

    if(request.method == 'POST'):

        decoded_uplink_data = decode_frm_payload(request.json["uplink_message"]["frm_payload"])

        # if we get the OTA trigger
        if(decoded_uplink_data == '\x01\x02\x03'):

            # send the ack
            json = insert_payload_in_json(last_sent)
            res = requests.post(push_url, json=json, headers=headers)
            log("uplinks", request.json)
            log("Time", "RETRANSMISSION OCCURRED!")
            log("Time", datetime.now().isoformat())
            

            return 'success', 200

        # if we're in data
        if(decoded_uplink_data == '\x03\x02\x01'):
            
            # send the next blob
            if(len(file_chunks)):
                
                blob = file_chunks.pop(0)
                last_sent = blob
                json = insert_payload_in_json(blob)

                res = requests.post(push_url, json=json, headers=headers)
                log("uplinks", request.json)
                log("Time", datetime.now().isoformat())
                return 'success', 200
            else:
                # res = requests.post(push_url, json=insert_payload_in_json('brontasaurus!'), headers=headers)
                log("Time", "RETRANSMISSION OF LENGTH (INCORRECT LENGTH)")
                log("uplinks", request.json)
                log("Time",datetime.now().isoformat())
                return 'success', 200

        res = requests.post(push_url, json=insert_payload_in_json(b'\x11'), headers=headers)
        
        log("uplinks", request.json)
        log("Time", datetime.now().isoformat())
        return 'success', 200


@app.route('/downlinks', methods=['POST'])
def webhook2():
    if(request.method == 'POST'):
        print(request.json)
        return 'success', 200

def log(log_name, data):
    try:
        with open(f"logs/{log_name}.log", 'a') as logFile:
            logFile.writelines(json.dumps(data) + "\n")
    except:
        with open(f"logs/{log_name}.log", 'w') as logFile:
            logFile.writelines(json.dumps(data) + "\n")

def insert_payload_in_json(data):
    edata = base64.b64encode(data).decode('utf-8')
    log("encoded_data", f"{data} : {edata}" )

    payload = {
        "downlinks":[{
        "f_port":2,
        "frm_payload": f"{edata}",
        }]
    }
    return payload


def decode_frm_payload(data):
    decoded_data = base64.b64decode(data).decode('utf-8')
    log("decoded_data", f"{data} : {decoded_data}" )
    return decoded_data

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
