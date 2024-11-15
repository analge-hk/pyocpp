import asyncio
from asyncio.tasks import FIRST_COMPLETED
import logging
import websockets
#from websockets.protocol import WebSocketServerProtocol
from CpChannelAbs import CpChannelAbs
from config import g_cp_config
from CpChannelCMS import CpChannelCMS
import task_websocket_debug

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

ws_server = None
async def start():  # start a websocket server
    global ws_server
    ws_server = await websockets.serve(ws_on_connect, '0.0.0.0', 9000, subprotocols=['ocpp1.6'],
                                       # if client has not implemented ping pong , it will cause disconnection issue
                                       ping_interval=None, ping_timeout=None, close_timeout=None)
    logger.info("pyWsProxy  Started listening '0.0.0.0:9000' to new connections...")
    await ws_server.wait_closed()


async def ws_on_connect(ws_cp: websockets, path):  # handle websocket client
    logger.info(f"ws_on_connect path={path}")

    # parse charge ID ------------------------------------------- config file cp id
    path_split = path.strip('/').split('/')
    config_cp_id = path_split[-1]

    # add ws debug function
    if(len(path_split) > 1 and path_split[0].lower()=="debug"):
        await task_websocket_debug.ws_debug_loop(config_cp_id, ws_cp)
        return await ws_cp.close()

    try:
        requested_protocols = ws_cp.request_headers['Sec-WebSocket-Protocol']
    except KeyError:
        logger.error("Client hasn't requested any Subprotocol.Closing Connection")
        return await ws_cp.close()

    if ws_cp.subprotocol:
        logger.info("Protocols Matched: %s", ws_cp.subprotocol)
    else:
        logger.warning('Protocols Mismatched | Expected Subprotocols: %s,'' but client supports  %s | Closing connection', ws_cp.available_subprotocols, requested_protocols)
        return await ws_cp.close()
    
    logger.info(f"websocket connect CP {config_cp_id}")

    # alway connect to PSN
    config_cms_list:dict = {}
    config_cms_list["PSN"] = {'cpId': config_cp_id, 'cms_server_name': 'PSN', 'cms_server_url': 'ws://localhost:9001', 'cms_main': True}
    
    # get cp config
    the_cp_config = g_cp_config.get(config_cp_id)
    if the_cp_config:
        cmsName = the_cp_config.get("cms_server_name","CMS").strip()
        cmsUrl = the_cp_config.get("cms_server_url","").strip()
        if len(cmsName)>0 and len(cmsUrl)>0:
            config_cms_list[cmsName] = the_cp_config
            config_cms_list["PSN"]["cms_main"] = False
            config_cms_list[cmsName]["cms_main"] = True
    logger.info(f"config_cms_list : {config_cms_list}")

    # register CP channel for handler cp message
    dict_channel = {}
    list_task = [asyncio.create_task(ws_cp_loop(config_cp_id, ws_cp, dict_channel))]
    for key in config_cms_list:
        # create channel object
        channel: CpChannelAbs = CpChannelCMS(name=key, id=config_cp_id, ws_cp=ws_cp, config=config_cms_list[key])
        dict_channel[key] = channel
        # create channel task and added to loop event
        list_task.append(asyncio.create_task(channel.start()))

    # wait task complete, and close all task when any task complete
    done, pending = await asyncio.wait(list_task, return_when=FIRST_COMPLETED)
    # for task in done:
    #     logger.error(f"{config_cp_id}: task done!")
    [task.cancel() for task in list_task]
    logger.error(f"{config_cp_id}: all task done!")

# loop of recv message from CP


async def ws_cp_loop(config_cp_id: str, ws_cp:websockets, dict_channel: dict):
    while True:
        try:
            message: str = await ws_cp.recv()
            logger.debug(f"{config_cp_id}: recv {message}")

            for channel in dict_channel.values():  # CP mesage route to all channel
                await channel.put(message)
        except websockets.exceptions.ConnectionClosed:
            logger.error(f"{config_cp_id}: Websockets Connection Closed!")
            return

if __name__ == '__main__':
    asyncio.run(start())
