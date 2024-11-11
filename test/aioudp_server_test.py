import asyncio
import asyncudp

async def main():
    sock = await asyncudp.create_socket(local_addr=('0.0.0.0', 8080))

    while True:
        data, addr = await sock.recvfrom()
        print(data, addr)
        sock.sendto(data, addr)

async def loop():
    while True:
        await asyncio.sleep(1)
        print("1")

async def start():
    await asyncio.gather(main(), loop())

asyncio.run(start())