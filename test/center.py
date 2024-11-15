import asyncio
import websockets
from datetime import datetime

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.v16 import call_result


class ChargePoint(cp):
    @on(Action.BootNotification)
    def on_boot_notitication(self, charge_point_vendor, charge_point_model, **kwargs):
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted
        )

    # Heartbeat response with current time in ISO8601 format
    @on(Action.Heartbeat)
    async def on_HeartBeat(self, **kwargs):
        print(kwargs)
        return call_result.HeartbeatPayload(current_time=str(datetime.utcnow().isoformat()[:-3]+'Z'))
    
    @on(Action.StatusNotification)
    async def on_status_notification(self, **kwargs):
        print(kwargs)
        return call_result.StatusNotificationPayload()

async def on_connect(websocket, path):
    """ For every new charge point that connects, create a ChargePoint instance
    and start listening for messages.

    """
    charge_point_id = path.strip('/')
    cp = ChargePoint(charge_point_id, websocket)

    try:
        await cp.start()
    except websockets.exceptions.ConnectionClosed:
        print(f"{charge_point_id} websocket close!")


async def main():
    server = await websockets.serve(
        on_connect,
        '0.0.0.0',
        80,
        subprotocols=['ocpp1.6']
    )

    await server.wait_closed()


if __name__ == '__main__':
    asyncio.run(main())