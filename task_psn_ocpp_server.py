import asyncio
import logging
import websockets
from config import *
from pyocppsrv import ChargePoint

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("psn-v8")

ws_server = None


async def start():
    # websocket server init and run
    global ws_server
    ws_server = await websockets.serve(ws_on_connect, '0.0.0.0', 9001, subprotocols=['ocpp1.6'],
                                       ping_interval=None,  # if client has not implemented ping pong , it will cause disconnection issue
                                       ping_timeout=None,
                                       close_timeout=None)
    logger.info("WebSocket Server Started listening '0.0.0.0:9001' to new connections...")
    await ws_server.wait_closed()


async def ws_on_connect(websocket, path):
    logger.info("websocket connect path=%s", path)

    try:
        requested_protocols = websocket.request_headers['Sec-WebSocket-Protocol']
    except KeyError:
        logger.error("Client hasn't requested any Subprotocol.Closing Connection")
        return await websocket.close()

    if websocket.subprotocol:
        logger.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        logger.warning('Protocols Mismatched | Expected Subprotocols: %s, but client supports  %s | Closing connection', websocket.available_subprotocols, requested_protocols)
        return await websocket.close()

    # Matching the charger id received with the id from config file , if it matches establish the connection
    path_split = path.strip('/').split('/')
    charge_point_id = path_split[-1]

    logger.info(f"{charge_point_id} websocket connected")
    the_cp = g_cp_ocpp[charge_point_id] = ChargePoint(charge_point_id, websocket)

    try:
        the_cp.connect_status = True
        await the_cp.start()
    except websockets.exceptions.ConnectionClosed:
        the_cp.connect_status = False
        logger.warning(f"{charge_point_id}: websockets closed!")

if __name__ == '__main__':
    asyncio.run(start())
