import asyncio
import json
import logging
import uuid
from ocpp.exceptions import NotImplementedError
from ocpp.messages import CallError
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp, call, call_result
from ocpp.v16.enums import *
import websockets
import sys
import datetime
import time
from ocpp.messages import Call, CallResult, unpack

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    @on(Action.BootNotification)
    def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        print("on_boot_notification")  
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status='Accepted'
        )

    @on(Action.StatusNotification)
    def on_status_notification(self, connector_id, error_code, status, **kwargs):
        print("on_status_notification")  
        self._metrics["Status"] = status  
        return call_result.StatusNotificationPayload()

    @on(Action.Authorize)
    def on_authorize(self, id_tag, **kwargs):
        print("on_authorize")  
        return call_result.AuthorizePayload(
            id_tag_info = { "status" : AuthorizationStatus.accepted }
        )

    @on(Action.StartTransaction)
    def on_start_transaction(self, connector_id, id_tag, meter_start, **kwargs):    
        print("on_start_transaction")  
        return call_result.StartTransactionPayload(
            id_tag_info = { "status" : AuthorizationStatus.accepted },
            transaction_id = 1234
        )
    
    @on(Action.StopTransaction)
    def on_stop_transaction(self, meter_stop, transaction_id, **kwargs):  
        print("on_stop_transaction")  
        return call_result.StopTransactionPayload(
            id_tag_info = { "status" : AuthorizationStatus.accepted }            
        )
    
    @on(Action.Heartbeat)
    def on_heartbeat(self, **kwargs):
        print("on_heartbeat")
        now = datetime.utcnow().isoformat()
        self._metrics["Heartbeat"] = now
        self._units["Heartbeat"] = "time"        
        return call_result.HeartbeatPayload(
            current_time=now
        )

    @on(Action.SetChargingProfile)
    def on_setChargingProfile(self, **kwargs):
        print("on_setChargingProfile")
        return call_result.SetChargingProfilePayload(status="Accepted")

    @on(Action.RemoteStartTransaction)
    def remote_start_transaction(self, id_tag):
        print("remote_start_transaction")
        return call_result.RemoteStartTransactionPayload(status=RemoteStartStopStatus.accepted)

    @on(Action.RemoteStopTransaction)
    def remote_stop_transaction(self, transaction_id):
        print("remote_stop_transaction")
        return call_result.RemoteStopTransactionPayload(status=RemoteStartStopStatus.accepted)

    @on(Action.TriggerMessage)
    def on_trigger_message(self, **kwargs):
        print("on_trigger_message 1")
        print("sleep 3")
        time.sleep(3)
        print("on_trigger_message 2")
        return call_result.TriggerMessagePayload(status=TriggerMessageStatus.accepted)

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charge_point_model="SingleSocketCharger",
            charge_point_vendor="WWWW",
            charge_point_serial_number='a',
            firmware_version="AC_DCE_2.t2AT"
        )
        response = await self.call(request)

#         # if response.status == RegistrationStatus.accepted:
#         #     print("Connected to central system.")
# # [2,"16240844","BootNotification",{"chargePointVendor":"WWWW","chargePointModel":"SingleSocketCharger","chargePointSerialNumber":"20211230000024","firmwareVersion":"AC_DCE_2.t2AT"}]
#         t = '[2,"16241407","BootNotification",{"chargePointVendor":"WWWW","chargePointModel":"SingleSocketCharger","chargePointSerialNumber":"2021230000024","firmwareVersion":"AC_DCE_2.t2AT"}]'
        # print(t)
        # await self._connection.send(t)

        while True:
            await asyncio.sleep(3)
            await self.call(call.HeartbeatPayload())
            await asyncio.sleep(3)
            await self.call(call.StatusNotificationPayload(1, ChargePointErrorCode.no_error, ChargePointStatus.preparing))
            await asyncio.sleep(3)
            await self.call(call.StatusNotificationPayload(1, ChargePointErrorCode.no_error, ChargePointStatus.charging))
            await asyncio.sleep(30)

wslink = 'ws://localhost:80'
async def main():
    print(f"Try Connect to {wslink}")
    async with websockets.connect(wslink, subprotocols=['ocpp1.6']) as ws:
        print(f"Connect to {wslink} success")
        cp = ChargePoint(chargeid, ws)
        await asyncio.gather(cp.start(), cp.send_boot_notification())

if __name__ == '__main__':
    cp = ChargePoint(None, None)
    payload = call.BootNotificationPayload("TEST","TEST")
    
    print(payload.__class__.__name__)

    ocppMessage = Call(
            unique_id=str(uuid.uuid4()),
            action=payload.__class__.__name__[:-7],
            payload=payload
        )

    # cp.call()
    json_str = ocppMessage.to_json()
    print(json_str)

    msg = unpack(json_str)
    print(msg)
