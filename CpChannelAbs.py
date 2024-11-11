import asyncio
import logging
from os import close
from websockets.protocol import WebSocketCommonProtocol
from ocpp.messages import Call, CallResult, CallError, unpack, pack
from ocpp.exceptions import OCPPError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

# register chanel for cp input message
class CpChannelAbs:
    def __init__(self, name, id, ws_cp:str, config:dict):
        self.id = id
        self.name = name
        self._queue = asyncio.Queue()
        self._ws_cp:WebSocketCommonProtocol = ws_cp
        self._config = config
        self.command_label_prefix = f"{self.name}-"
        
    async def recv(self): # CP->CMS
        while True:
            message = await self._queue.get()
            # logger.info(f"{self.id} CP->{self.name} real: {message}")
            new_message = self.router_filter_cp_to_cms(message)
            if new_message is not None:
                return new_message

    async def send(self, message):  # CMS->CP
        new_message = self.router_filter_cms_to_cp(message)
        if new_message is not None:
            await self._ws_cp.send(new_message)
            # logger.info(f"{self.id} {self.name}->CP real: {new_message}")
        return new_message
    async def close(self):
        pass

    async def put(self, message):
        await self._queue.put(message)# cp recv message and put to queue

    async def start(self):
        while True:
            message = await self.recv()
            # logger.info(f"{self.id}: {self.name} recv: {message}")

    # filter CMS -> CP
    def router_filter_cms_to_cp(self, message):
        try:
            msg = unpack(message)
        except OCPPError as e:
            logger.error(f"{self.id}: CMS->CP parse error{message}")
            return None

        if isinstance(msg, Call): # CMS->CP need add uuid prefix
            call:Call = msg
            call.unique_id = self.command_label_prefix + call.unique_id
            return pack(call)
        elif isinstance(msg, CallResult) or isinstance(msg, CallError):
            if self._config.get("cms_main",False): # Only the main CMS can reply to CP
                return message
        return None

    # filter CP -> CMS
    def router_filter_cp_to_cms(self, message):
        try:
            msg = unpack(message)
        except OCPPError as e:
            logger.error(f"{self.id}: CP->CMS parse error{message}")
            return None

        if isinstance(msg, Call):
            return message
        elif isinstance(msg, CallResult) or isinstance(msg, CallError):
            callResult:CallResult = msg
            if callResult.unique_id.startswith(self.command_label_prefix): # CP only replies to the sender
                callResult.unique_id = callResult.unique_id[len(self.command_label_prefix):] # remove uuid prefix
                return pack(callResult)
        else:
            return None
