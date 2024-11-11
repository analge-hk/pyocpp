import asyncio
import websockets
import sys

ws_url = "ws://localhost:9001/cmd"
help_text = '''You can send command to OCPP server by the program
Usage: <CP num> <command> <command arg>
help
exit
1 start                                                     [send command "RemoteStartTransaction" to CP1]
2 stop                                                      [send command "RemoteStopTransaction" to CP2]
2 status                                                    [trigger message "StatusNotification" to CP2]
1 limit 30                                                  [send command "UpdateFirmware" to CP1]
1 update http://65.52.164.18:8000/download/zwzx-v1.12.20.mzip      [send command "UpdateFirmware" to CP1]
2 qrcode https://open.delightintl.com/qrcode/scanin/607     [set qrcode url for CP2]
2 debug                                                     [send debug command to CP2]
2 getconfig                                                 [send getconfig to CP2]
2 setconfig MeterValueSampleInterval 20                     [send setconfig MeterValueSampleInterval=20 to CP2]
'''
# send command to OCPP server
async def send_msg(websocket):
    while True:
        _text = input("please enter command: ")
        if _text == "help":
            print(help_text)
            continue
        elif _text == "exit":
            await websocket.close(reason="user exit")
            return False

        await websocket.send(_text)
        recv_text = await websocket.recv()
        print(f"{recv_text}")

async def main_logic():
    async with websockets.connect(ws_url) as websocket:
        await send_msg(websocket)


if __name__ == '__main__':
    arg_len = len(sys.argv)
    arg_vars = list(sys.argv)
    if(arg_len>1):
        ws_url = arg_vars[1]

    print(help_text)

    print(f'connect to ocpp server {ws_url}')
    asyncio.get_event_loop().run_until_complete(main_logic())
