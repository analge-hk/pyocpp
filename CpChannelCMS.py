import asyncio
from CpChannelAbs import CpChannelAbs
import logging
import websockets
from websockets.protocol import WebSocketCommonProtocol
import config

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

CP = config.config_file["cp"]

class CpChannelCMS(CpChannelAbs):
    async def ws_cms_recv_loop(self, evt:asyncio.Event): # recv CMS messsage
        cms_server_url = self._config.get("cms_server_url", None)
        if cms_server_url is None:
            logger.error(f"{self.id} Not found cms_server_url!")
            return

        cms_cp_id = self._config.get("cms_cp_id", self.id)
        wslink = f"{cms_server_url}/{cms_cp_id}"
        logger.info(f"try to connect ocpp server {wslink}")
        async with websockets.connect(wslink, subprotocols=['ocpp1.6']) as ws_cms: # connect to CMS server
            self._ws_cms = ws_cms
            logger.info(f"connect to {wslink} success.")
            
            evt.set() # Mark CMS successfully connected

            while True: # recv CMS message
                try:
                    message = await self._ws_cms.recv() # CMS -> CP
                    new_message = await self.send(message)
                    if new_message is not None:
                        logger.info(f"{self.id} {self.name}->CP: {message}")
                except websockets.exceptions.ConnectionClosed as e:
                    logger.warn(f"{self.id} {self.name} websocket close! {repr(e)}")
                    return    

    async def ws_cp_recv_loop(self, evt:asyncio.Event): # recv CP message
        await evt.wait() # wait for connect to CMS

        while True: # recv CP message
            try:
                message = await self.recv() 
                await self._ws_cms.send(message)  # CP -> CMS
                logger.info(f"{self.id} CP->{self.name}: {message}")
            except websockets.exceptions.ConnectionClosed as e:
                logger.warn(f"{self.id} {self.name} websocket close! {repr(e)}")
                return
        
    async def start(self):
        evt = asyncio.Event() # create asyncio event for mark CMS connected
        await asyncio.gather(self.ws_cms_recv_loop(evt), self.ws_cp_recv_loop(evt))
        

async def main():
    from task_proxy_server import start
    await asyncio.gather(start())

if __name__ == '__main__':
    asyncio.run(main())
    