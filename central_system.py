import asyncio
import logging
import task_psn_ocpp_server
import nest_asyncio
import task_proxy_server
import task_udp
import task_duration
import task_modbus_async
from config import *

nest_asyncio.apply()

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("central")

async def main():
    tasks = [task_psn_ocpp_server.start(),task_proxy_server.start(),task_udp.start(),task_duration.start(),task_modbus_async.start()]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    logger.info("ocpp server start!")
    asyncio.run(main())
