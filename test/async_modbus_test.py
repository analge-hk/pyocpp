from asyncio.tasks import FIRST_COMPLETED, sleep
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import _thread

# exe = ThreadPoolExecutor(2)

#  # 获取新的事件循环
# loop = asyncio.get_event_loop()
# loop.set_default_executor(exe)
# 设置当前事件循环
# asyncio.set_event_loop(loop)

def long_blocking_function():
    print(time.time())
    time.sleep(2)
    return True
 
 
async def run():
    while True:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, long_blocking_function)
 
 
async def main_loop():
    while True:
        await asyncio.sleep(1)
        print("**")

async def main():
    now = time.time()
    await asyncio.gather(run(), main_loop())
    print(time.time() - now)

async def t1(i):
    await asyncio.sleep(1)
    return i+2

def start():
    a = asyncio.run(t1(2))
    print(a)

async def main():
    # create new mqtt thread and run start
    _thread.start_new_thread(start, ())

    await asyncio.gather(main_loop())

async def a():
    print('Suspending a')
    await asyncio.sleep(3)
    print('Resuming a')


async def b():
    print('Suspending b')
    await asyncio.sleep(1)
    print('Resuming b')
    await asyncio.gather(c(), d())

async def c():
    print('Suspending c')
    await asyncio.sleep(5)
    print('Resuming c')

async def d():
    print('Suspending d')
    await asyncio.sleep(6)
    print('Resuming d')

def show_perf(func):
    print('*' * 20)
    start = time.perf_counter()
    asyncio.run(func())
    print(f'{func.__name__} Cost: {time.perf_counter() - start}')

async def c3():
    print("1"*20)
    task1 = asyncio.create_task(a())
    print("1"*20)
    task2 = asyncio.create_task(b())
    print("1"*20)
    await task2
    print("2"*20)
    await task1
    print("3"*20)

async def c4():
    task = asyncio.create_task(b())
    await a()
    await task

async def c5():
    task1 = asyncio.create_task(a())
    task2 = asyncio.create_task(b())
    task1.set_name("TT1")
    task2.set_name("TT2")
    # await asyncio.gather(*tasks)
    # task1.cancel()
    # done, pending = await asyncio.wait((task1, task2), return_when=FIRST_COMPLETED)
    # for t in done:
    #     print("done" +" " +t.get_name())
    # for t in pending:
    #     print("pending" +" " +t.get_name())
    # await asyncio.gather(task1, task2)
    await asyncio.wait([task1, task2], return_when=FIRST_COMPLETED)
    print("x")
    ttt= asyncio.Task.current_task()
    print("current_task="+ttt.get_name())
    ttt= asyncio.Task.all_tasks()
    [print("all task "+t.get_name()) for t in ttt]
    await asyncio.sleep(10)
    print("y")

if __name__ == '__main__':
    # asyncio.run(main())
    # show_perf(c3)
    # show_perf(c4)
    show_perf(c5)


# if __name__ == '__main__':
#     # asyncio.run(main())
#     # s = "PI/OCPP/UP/"  #ocpp payload 上传
#     # n = s.strip("/").split('/')[-1]
#     # print(n)

#     # create new mqtt thread and run start
#     _thread.start_new_thread(start, ())

#     # a = asyncio.run(t1(2))
#     # print(a)

#     while True:
#         pass
