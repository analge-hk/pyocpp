import asyncio

def f1():
    print("f1 start")
    # f2()
    asyncio.create_task(f2())
    print("f1 end")

async def f2():
    print("f2 start")
    await asyncio.sleep(1)
    print("f2 end")

async def main():
    f1()
    await f2()


asyncio.run(main())