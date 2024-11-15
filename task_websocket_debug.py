import logging
import websockets
from config import *
from pyocppsrv import ChargePoint, Connector
#from websockets.protocol import WebSocketCommonProtocol

# recv remote websocket OCPP message and send to CP

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wsdbg")
async def ws_debug_loop(config_cp_id: str, ws_cp:websockets):
    the_cp: ChargePoint = g_cp_ocpp.get(config_cp_id)
    if not the_cp:
        logger.warning(f"not found the cpId {config_cp_id}.")
        return
    
    logger.info(f"{config_cp_id}: start websocket debug")
    while True:
        try:
            # recv message from remote web websocket online tool
            message: str = await ws_cp.recv()
            logger.info(f"{config_cp_id}: DBG->CP {message}")

            # send ocpp message to CP
            await the_cp.websocket.send(message)
            # logger.info(f"{config_cp_id}: CP->DBG {response}")
            # send CP respone to websocket
            # if(response):
            #     await ws_cp.send(f"{response.status}")
        except websockets.exceptions.ConnectionClosed:
            logger.error(f"{config_cp_id}: Websockets Connection Closed!")
            return
        except Exception as e:
            logger.error(f'{config_cp_id}: ' + repr(e))


