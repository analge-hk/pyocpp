import socket
import sys
import json

# {"cpId":"1301", "method":"getconfig"}

if len(sys.argv) > 2:
    server_ip = sys.argv[1]
    data = sys.argv[2]
else:
    print("err command sample.")
    print("python3 pydup.py 127.0.0.1 '{\\\"cpId\\\":\\\"1301\\\", \\\"method\\\":\\\"getconfig\\\"}'")
    sys.exit()

addr=(server_ip,8080)
print(f"udp connect to {addr}")
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.settimeout(5)
print(f"udp send to {data}")
s.sendto(data.encode("utf-8"),addr)
response = s.recv(10240)
payload_str = response.decode('UTF-8', 'ignore').strip().strip(b'\x00'.decode())
json_data = json.loads(payload_str)
json_str = json.dumps(json_data, indent=2,ensure_ascii=False)
print(json_str)

s.close()