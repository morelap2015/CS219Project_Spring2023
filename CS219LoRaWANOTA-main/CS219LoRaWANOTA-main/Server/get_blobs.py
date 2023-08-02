# splits a file into chunks of 64 bytes
def get_blobs_from_file(filename):
    
    chunksize = 40
    list_of_chunks = []
    
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunksize)
            if chunk:
                list_of_chunks.append(chunk)
            else:
                break
    
    return list_of_chunks

if __name__ == "__main__":
    print(get_blobs_from_file("thisisatest.txt"))