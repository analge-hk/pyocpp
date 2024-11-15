import asyncio
import logging
import websockets
from os import close
#from websockets.protocol import WebSocketCommonProtocol
from ocpp.messages import Call, CallResult, CallError, unpack, pack
from ocpp.exceptions import OCPPError
from ocpp.v16 import enums
from config import g_connector
from pyocppsrv import Connector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

# register chanel for cp input message
class CpChannelAbs:
    def __init__(self, name, id, ws_cp:str, config:dict):
        self.id = id
        self.name = name
        self._queue = asyncio.Queue()
        self._ws_cp:WebSocket = ws_cp
        self._config = config
        self.command_label_prefix = f"{self.name}-"
        self.is_psn = self.name.startswith("PSN")
        
    async def recv(self): # CP->CMS
        while True:
            message = await self._queue.get()
            # logger.warning(f"{self.id} CP->{self.name} real: {message}")
            new_message = self.router_filter_cp_to_cms(message)
            if new_message is not None:
                return new_message

    async def send(self, message):  # CMS->CP
        new_message = self.router_filter_cms_to_cp(message)
        if new_message is not None:
            await self._ws_cp.send(new_message)
            # logger.warning(f"{self.id} {self.name}->CP real: {new_message}")
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
            if self.is_psn:
                call.unique_id = self.command_label_prefix + call.unique_id
                return pack(call)
            else:
                return message
        elif isinstance(msg, CallResult) or isinstance(msg, CallError):
            if self._config.get("cms_main",False): # Only the main CMS can reply to CP
                # [3,"a1d937fe-a980-6e24-9065-7a6724fa17ee",{"idTagInfo":{"expiryDate":"2023-10-13T05:32:59.430Z","parentIdTag":"659508192","status":"Accepted"},"transactionId":291076}]
                # when CMS/PSN send StartTransaction ACK, get transactionID from payload
                callResult:CallResult = msg
                if callResult.payload.get("idTagInfo"):
                    transactionId = callResult.payload.get("transactionId")
                    if transactionId:
                        for the_connector in g_connector.values():
                            if the_connector.last_StartTransaction_uuid == callResult.unique_id:
                                the_connector.transaction_id = transactionId
                                logger.info(f"{the_connector.id} from StartTransaction get transactionId is {transactionId}")
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
            # [2,"a1d937fe-a980-6e24-9065-7a6724fa17ee","StartTransaction",{"connectorId":1,"idTag":"202310120532589566","meterStart":6518,"timestamp":"2023-10-11T21:32:58Z"}]
            # when connector send StartTransaction to save uuid
            call:Call = msg
            if call.action == enums.Action.StartTransaction:
                self.id
                connectorId = call.payload.get("connectorId")
                the_connector:Connector = g_connector.get(f"{self.id}-{connectorId}")
                if the_connector:
                    the_connector.last_StartTransaction_uuid = call.unique_id
            return message
        elif isinstance(msg, CallResult) or isinstance(msg, CallError):
            callResult:CallResult = msg
            if self.is_psn and callResult.unique_id.startswith("PSN"): # # PSN call, CP callResult
                callResult.unique_id = callResult.unique_id[len(self.command_label_prefix):] # remove uuid prefix
                return pack(callResult)
            elif (not self.is_psn) and (not callResult.unique_id.startswith("PSN")):# CMS call, CP callResult
                return message
            else:
                return None
        else:
            return None
