import asyncio
import datetime
import json
from config import *
from pyocppsrv import ChargePoint, Connector
import asyncudp  # pip install import asyncudp
import logging
from ocpp.v16 import enums
from task_find_gc import get_gc_ip

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("udp")

local_ip = "0.0.0.0"
local_port = 8080
server_port = 9988

CODE_OK = 200
CODE_FAIL = -1

asyncudp_sock = None

async def udp_send(addr, obj={}):
    global asyncudp_sock, g_gc_ip, server_port
    payload_str = json.dumps(obj)
    bytes_data = payload_str.encode("utf-8")
    logger.debug(f"send {addr} {payload_str}")
    asyncudp_sock.sendto(bytes_data, addr)

async def udp_recv():
    global asyncudp_sock
    while True:
        try:
            data, addr = await asyncudp_sock.recvfrom()
            payload_str = data.decode('UTF-8', 'ignore').strip().strip(b'\x00'.decode())
            await handler_recv(addr, payload_str)
        except Exception as e:
            logger.error(e)

async def start():
    global g_gc_ip
    while not g_gc_ip:
        await asyncio.sleep(1)
        g_gc_ip = get_gc_ip()
    logger.info(f"find GC ip is {g_gc_ip}")

    global asyncudp_sock
    logger.info(f"start listen {local_ip}:{local_port}")
    asyncudp_sock = await asyncudp.create_socket(local_addr=(local_ip, local_port))
    await asyncio.gather(udp_recv(), udp_loop())

async def handler_recv(addr, payload_str):
    logger.debug(f"recv {addr} payload={payload_str}")

    # parse json
    try:
        json_data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        logger.warning("recv json JSONDecodeError " + repr(e)  + " " + payload_str)
        return

    # pass for master-box-setOcppRemote-ack
    code = json_data.get("code")
    if code:
        return

    cpId = json_data.get("cpId")
    if not cpId:
        logger.warning("missing field cpId")
        return

    the_cp: ChargePoint = g_cp_ocpp.get(cpId)
    if not the_cp:
        logger.warning(f"not found the cpId {cpId}.")
        return

    method = json_data.get("method")
    if method:
        logger.info(f"recv {addr} payload={payload_str}")


    connectorId = json_data.get("connectorId", 1)
    the_connector:Connector = g_connector.get(f"{cpId}-{connectorId}")

    if method=="start":
        if not the_connector:
            await udp_send(addr=addr, obj={"method":method, "response": "not found the connector"})
            return
        await the_connector.remote_start()
        await udp_send_report(the_connector)
        return
    elif method=="stop":
        if not the_connector:
            await udp_send(addr=addr, obj={"method":method, "response": "not found the connector"})
            return
        await the_connector.remote_stop()
        await udp_send_report(the_connector)
        return
    elif method=="setPowerRate":
        if not the_connector:
            await udp_send(addr=addr, obj={"method":method, "response": "not found the connector"})
            return
        powerRate = int(float(json_data.get("powerRate", 32)))
        await the_connector.set_power_rate(powerRate)
        await udp_send_report(the_connector)
        return
    elif method == "setCurrentLimit":
        if not the_connector:
            await udp_send(addr=addr, obj={"method":method, "response": "not found the connector"})
            return
        currentLimit = int(float(json_data.get("currentLimit", 32)))
        await the_connector.set_current_limit(currentLimit)
        await udp_send_report(the_connector)
        return
    elif method == "setCurrentLimitDefault":
        if not the_connector:
            await udp_send(addr=addr, obj={"method":method, "response": "not found the connector"})
            return
        currentLimit = int(float(json_data.get("currentLimit", 32)))
        await the_connector.set_current_limit_default(currentLimit)
        await udp_send_report(the_connector)
        return
    elif method == "qrcode":
        response = await the_cp.set_qrcode(json_data.get("qrcode"))
        await udp_send(addr=addr, obj={"method":method, "response":str(response)})
        return
    elif method == "debug":
        response = await the_cp.send_debug()
        await udp_send(addr=addr, obj={"method":method, "response":str(response)})
        return
    elif method == "getconfig":
        response = await the_cp.get_config()
        await udp_send(addr=addr, obj={"method":method, "response":str(response)})
        return
    elif method == "setconfig":
        key = json_data.get("key")
        value = json_data.get("value")
        response = await the_cp.set_config(key, value)
        await udp_send(addr=addr, obj={"method":method, "response":str(str(response))})
        return
    elif method == "updateFirmware":
        response = await the_cp.update_firmware(json_data.get("url"))
        await udp_send(addr=addr, obj={"method":method, "response":str(response)})
        return
    else:
        await udp_send(addr=addr, obj={"err":"unknow method"})
        return

async def udp_loop():
    global asyncudp_sock
    i = 0
    while True:
        await asyncio.sleep(10)
        i = i + 1
        if (i % 6) == 0: # get status per minute
            for the_cp in g_cp_ocpp.values():
                try:
                    await the_cp.trigger_status_notification()
                except Exception as e:
                    logger.error(repr(e))
        for the_connector in g_connector.values():
            try:
                the_connector.print_info()
                await udp_send_report(the_connector)
                await asyncio.sleep(.1)
            except Exception as e:
                logger.error(repr(e))

async def udp_send_report(the_connector: Connector):
    if the_connector.isOnline():
        cp_report = the_connector.get_report()
        cp_obj = {"method": "setOcppReport", "params": cp_report }
        global g_gc_ip, server_port
        await udp_send(addr=(g_gc_ip, server_port), obj=cp_obj)

if __name__ == '__main__':
    asyncio.run(start())

"""
test step
1 run udp tool
2 connect to pi
3 send udp msg

{"cpId":"000080001", "method":"start"}
{"cpId":"1301", "method":"getconfig"}

"""
