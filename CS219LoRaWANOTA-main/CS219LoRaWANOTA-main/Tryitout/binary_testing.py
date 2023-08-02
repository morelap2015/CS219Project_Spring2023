import struct
import base64
import codecs
# import the time module
import time

filename = "fipy.bin"
start_time = time.time()
num_iterations = 0
chunksize = 64
list_of_chunks = []
with open(filename, "rb") as f:
    while True:
        num_iterations +=1
        chunk = f.read(chunksize)
        if chunk:
            # print(chunk)
            # print(type(chunk))
            # print(base64.b64encode(chunk).decode("utf-8"))
            list_of_chunks.append(chunk)
        else:
            break

# print(list_of_chunks)
end_time = time.time()
# Last index +1
print(len(list_of_chunks))
print("Took {} seconds to index binary file".format(end_time-start_time))