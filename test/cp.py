import asyncio
import logging
from ocpp.exceptions import NotImplementedError
from ocpp.messages import CallError
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp, call, call_result
from ocpp.v16.enums import *
import websockets
import sys
import datetime
import time
import random

logging.basicConfig(level=logging.DEBUG)

g_status: ChargePointStatus = ChargePointStatus.available


class ChargePoint(cp):
    @on(Action.BootNotification, skip_schema_validation=True)
    def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        print("on_boot_notification")
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status='Accepted'
        )

    @on(Action.StatusNotification, skip_schema_validation=True)
    def on_status_notification(self, connector_id, error_code, status, **kwargs):
        print("on_status_notification")
        self._metrics["Status"] = status
        return call_result.StatusNotificationPayload()

    @on(Action.Authorize, skip_schema_validation=True)
    def on_authorize(self, id_tag, **kwargs):
        print("on_authorize")
        return call_result.AuthorizePayload(
            id_tag_info={"status": AuthorizationStatus.accepted}
        )

    @on(Action.StartTransaction, skip_schema_validation=True)
    def on_start_transaction(self, connector_id, id_tag, meter_start, **kwargs):
        print("on_start_transaction")
        return call_result.StartTransactionPayload(
            id_tag_info={"status": AuthorizationStatus.accepted},
            transaction_id=1234
        )

    @on(Action.StopTransaction, skip_schema_validation=True)
    def on_stop_transaction(self, meter_stop, transaction_id, **kwargs):
        print("on_stop_transaction")
        return call_result.StopTransactionPayload(
            id_tag_info={"status": AuthorizationStatus.accepted}
        )

    @on(Action.Heartbeat, skip_schema_validation=True)
    def on_heartbeat(self, **kwargs):
        print("on_heartbeat")
        now = datetime.utcnow().isoformat()
        self._metrics["Heartbeat"] = now
        self._units["Heartbeat"] = "time"
        return call_result.HeartbeatPayload(
            current_time=now
        )

    @on(Action.SetChargingProfile, skip_schema_validation=True)
    def on_setChargingProfile(self, **kwargs):
        print("on_setChargingProfile")
        return call_result.SetChargingProfilePayload(status="Accepted")

    @on(Action.RemoteStartTransaction, skip_schema_validation=True)
    def remote_start_transaction(self, **kwargs):
        print("remote_start_transaction")
        global g_status
        g_status = ChargePointStatus.charging
        return call_result.RemoteStartTransactionPayload(status=RemoteStartStopStatus.accepted)

    @on(Action.RemoteStopTransaction, skip_schema_validation=True)
    def remote_stop_transaction(self, transaction_id):
        print("remote_stop_transaction")
        global g_status
        g_status = ChargePointStatus.preparing
        return call_result.RemoteStopTransactionPayload(status=RemoteStartStopStatus.accepted)

    @on(Action.TriggerMessage, skip_schema_validation=True)
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
            firmware_version="AC_DCE_2.t2AT",
            # charge_point_serial_number=self.id
            charge_point_serial_number="xxx"
        )
        response = await self.call(request)

#         # if response.status == RegistrationStatus.accepted:
#         #     print("Connected to central system.")
# # [2,"16240844","BootNotification",{"chargePointVendor":"WWWW","chargePointModel":"SingleSocketCharger","chargePointSerialNumber":"20211230000024","firmwareVersion":"AC_DCE_2.t2AT"}]
#         t = '[2,"16241407","BootNotification",{"chargePointVendor":"WWWW","chargePointModel":"SingleSocketCharger","chargePointSerialNumber":"2021230000024","firmwareVersion":"AC_DCE_2.t2AT"}]'
        # print(t)
        # await self._connection.send(t)

        Current = 10
        Voltage = 220
        Energy = 3184
        
        while True:
            await asyncio.sleep(10)
            await self.call(call.HeartbeatPayload())
            await self.call(call.StatusNotificationPayload(1, ChargePointErrorCode.no_error, g_status))
            # May 11 16:43:01 psnsrv python3[1159]: INFO:proxy:100370004 CP->PSN: [2,"a8a940e4-59ba-99e1-6f4d-e9e727744d1b","MeterValues",{"connectorId":1,"transactionId":1,"meterValue":[{"timestamp":"2022-05-11T08:43:01Z","sampledValue":[{"value":"226.90","context":"Sample.Periodic","format":"Raw","measurand":"Voltage","phase":"L1-N","location":"Body","unit":"V"},{"value":"0.19","context":"Sample.Periodic","format":"Raw","measurand":"Current.Import","phase":"L1-N","location":"Body","unit":"A"},{"value":"3184","context":"Sample.Periodic","format":"Raw","measurand":"Energy.Active.Import.Register","location":"Body","unit":"Wh"}]}]}]

            Current += random.randint(-2, 2)
            Voltage += random.randint(-2, 2)
            Energy = Energy + 1

            meter_value = [{
                                "timestamp": "2022-05-11T08:43:01Z",
                                "sampledValue": [
                                {
                                    "value": str(Voltage),
                                    "context": "Sample.Periodic",
                                    "format": "Raw",
                                    "measurand": "Voltage",
                                    "phase": "L1-N",
                                    "location": "Body",
                                    "unit": "V"
                                },
                                {
                                    "value": str(Current),
                                    "context": "Sample.Periodic",
                                    "format": "Raw",
                                    "measurand": "Current.Import",
                                    "phase": "L1-N",
                                    "location": "Body",
                                    "unit": "A"
                                },
                                {
                                    "value": str(Energy),
                                    "context": "Sample.Periodic",
                                    "format": "Raw",
                                    "measurand": "Energy.Active.Import.Register",
                                    "location": "Body",
                                    "unit": "Wh"
                                }
                                ]
                            }]

            await self.call(call.MeterValuesPayload(1, meter_value))


wslink = 'ws://54.151.248.8:6670/ocppj/10403353'
chargeid = '10403353'


async def main():
    while True:
        print(f"Try Connect to {wslink}")
        async with websockets.connect(wslink, subprotocols=['ocpp1.6']) as ws:
            print(f"Connect to {wslink} success")
            cp = ChargePoint(chargeid, ws)
            await asyncio.gather(cp.start(), cp.send_boot_notification())
        await asyncio.sleep(5)

if __name__ == '__main__':
    arg_len = len(sys.argv)
    arg_vars = list(sys.argv)
    if(arg_len > 1):
        wslink = arg_vars[1]
    if(arg_len > 2):
        chargeid = arg_vars[2]

    asyncio.run(main())
