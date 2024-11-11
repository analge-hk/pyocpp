import asyncio
import logging
import socket
import asyncudp

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("findGC")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        return ip
    except Exception as e:
        logger.error(e)
    finally:
        s.close()

def get_gc_ip():
    ip = get_local_ip()
    if not ip:
        return
    index = ip.rfind('.')
    bip = ip[:index] + ".255"

    send_bytes = bytes.fromhex("FF 01 01 02")
    dest = (bip, 1500)
    udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        udp_client_socket.sendto(send_bytes, dest)
        udp_client_socket.settimeout(3)
        data, server_addr = udp_client_socket.recvfrom(1024)
        gc_ip = server_addr[0]
        return gc_ip
    except Exception as e:
        print(e)

    udp_client_socket.close()


async def start():
    gc_ip = None
    while not gc_ip:
        gc_ip = get_gc_ip()
    logger.info(f'Find GC IP={gc_ip}')

    asyncudp_sock = await asyncudp.create_socket(local_addr=("0.0.0.0", 8080))
    data, addr = await asyncudp_sock.recvfrom()
    print(data, addr)

if __name__ == '__main__':
    # asyncio.run(start())
    ip = get_local_ip()
    print(ip)
