import asyncio
import logging
from typing import Union
from websockets import WebSocketServerProtocol
from dataclasses import dataclass
from task_mqtt import mqtt_send_pi_ocpp_up

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

@dataclass
class websocket_proxy():
    _connection: WebSocketServerProtocol
    _charge_point_id: str

    async def send(self, message):
        logger.debug('%s: send %s',self._charge_point_id, message)
        await self._connection.send(message)

    async def recv(self):
        message = await self._connection.recv()
        logger.debug('%s: recv %s',self._charge_point_id, message)
        mqtt_send_pi_ocpp_up(self._charge_point_id, message)
        return message

    async def close(self):
        await self._connection.close()

if __name__ == '__main__':
    pass
