# coding=utf-8
import asyncio
import functools



async def test (event:asyncio.Event):
    while True:
        print("test event="+str(event.is_set()))
        await event.wait()
        print('triggered')
        await asyncio.sleep(0.5)

async def test_set (event:asyncio.Event):
    while True:
        print("test_set event="+str(event.is_set()))
        await asyncio.sleep(1)
        print('set event')
        event.set()
        print('clear')
        event.clear()
        await asyncio.sleep(3)
        # print('finis')

async def main ():
    event = asyncio.Event()
    print(event.is_set())
    await asyncio.gather(test(event),test_set(event))

if __name__ == '__main__':
    asyncio.run(main())

