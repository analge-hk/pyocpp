import asyncio
from email.policy import default
import logging
from time import sleep
from pyModbusTCP.client import ModbusClient
from config import *
from pyocppsrv import ChargePoint
from concurrent.futures import ThreadPoolExecutor
 
# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("modbus")

CP_count = len(g_cp_config)
mbs_value_dac_new = [0]*CP_count  # Device DAC value modbus registers
mbs_value_onoff_new = [0]*CP_count  # Scene ON/OFF modbus registers
modbus_client:ModbusClient = None

# create defualt thread pool
loop = asyncio.get_event_loop()
exe = ThreadPoolExecutor(2)
asyncio.get_event_loop().set_default_executor(exe)

def get_modbus_data():
    # Adding modbus communication client
    global modbus_client, CP_count, config_file, mbs_value_onoff_new, mbs_value_dac_new

    # Fix bug for close the connection after each read data
    if not isinstance(modbus_client, ModbusClient):
        modbus_client = ModbusClient(host=config_file['modbus_host'], port=502, unit_id=config_file['modbus_slave_id'], auto_open=True, auto_close=False)

    # Get Modbus data from GC
    try:
        mbs_value_onoff_new = modbus_client.read_holding_registers(config_file['modbus_scene_onoff_reg_start'], CP_count)
        sleep(1)
        mbs_value_dac_new = modbus_client.read_input_registers(config_file['modbus_device_dac_reg_start'], CP_count)
    except TypeError:
        logger.warning('No Modbus data received from GC')

    logger.info(f"Get GC MODBUS Scene ONOFF: {mbs_value_onoff_new}")
    logger.info(f"Get GC MODBUS Device DAC:  {mbs_value_dac_new}")

async def start():
    logger.info("MODBUS start")
    while True:
        await asyncio.sleep(5)

        # sync function -> async function
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, get_modbus_data)

        # Write back device data Modbus data to GC
        await write_back_modbus_data_device_data()
        if(mbs_value_onoff_new == None or mbs_value_dac_new == None):
            logger.warning('No Modbus data received from GC')
            continue

        for cpid, the_cp in g_cp_ocpp.items():
            i = the_cp.cp_num
            if(isinstance(the_cp, ChargePoint) and the_cp.connect_status == True):
                try:
                    # try to set the CP ON/OFF
                    await the_cp.process_modbus_data_onoff(mbs_value_onoff_new[i], mbs_value_dac_new[i])
                    # try to set the CP current limit
                    await the_cp.process_modbus_data_dac(mbs_value_dac_new[i])
                    # await the_cp.get_composite_schedule_status()
                    if the_cp.cp_status == None:
                        await the_cp.trigger_status_notification()   # Try to get StatusNotification,
                    the_cp.print_info()  # print cp stats
                    # request meter values
                    #await the_cp.trigger_meter_values()
                except asyncio.TimeoutError:
                    logger.error(f'{the_cp.id}: CP{the_cp.num} TimeoutError.')
                    # The network is abnormal, waiting for the CP to reconnect
                    await the_cp.close()
                except Exception as e:
                    logger.error(f'{the_cp.id}: CP{the_cp.num} ' + repr(e))
                    # await the_cp.close()

        await write_back_modbus_data_scene_onoff("")  # Write back CP status Modbus data to GC


async def write_back_modbus_data_scene_onoff(cpid:str):
    # sync CP status with Modbus DATA
    global mbs_value_onoff_new
    if(isinstance(mbs_value_dac_new, list) and len(mbs_value_dac_new) == CP_count):
        for cpid, the_cp in g_cp_ocpp.items():
            i = the_cp.num - 1
            if(isinstance(the_cp, ChargePoint) and the_cp.cp_status != None and the_cp.connect_status == True):
                if((mbs_value_onoff_new[i] > 0) != the_cp.charing_start):
                    mbs_value_onoff_new[i] = (1 if the_cp.charing_start else 0)

                    try:
                        mbs_reg_address = config_file['modbus_scene_onoff_reg_start'] + i
                        modbus_client.write_single_register(mbs_reg_address, mbs_value_onoff_new[i])
                        logger.info(f"{the_cp.id}: Set GC MODBUS Scene ONOFF CP{i+1} {mbs_value_onoff_new[i]}")
                    except TypeError:
                        logger.error(f"{the_cp.id}: Set GC MODBUS Scene ONOFF CP{i+1} error!")


async def write_back_modbus_data_device_data():
    for cpid, the_cp in g_cp_ocpp.items():
        i = the_cp.num - 1
        is_ocpp_meter_value = g_cp_config.get("ocpp_meter_value", False)
        if(isinstance(the_cp, ChargePoint) and the_cp.cp_status != None and the_cp.connect_status == True and is_ocpp_meter_value):
            meter_value_power = int(the_cp.meter_value_current * the_cp.meter_value_voltage / 1000) # unitma x V /1000 = W
            mbs_value = [the_cp.meter_value_current, the_cp.meter_value_voltage, meter_value_power]
            try:
                # Register address current offset = 5002 + DeviceID * 10
                mbs_reg_address = config_file['modbus_device_current_reg_start'] + ((the_cp.num)*10)
                modbus_client.write_multiple_registers(mbs_reg_address, mbs_value)
                logger.debug(f"{the_cp.id}: Set GC MODBUS Device DATA: [CP{the_cp.num} current={mbs_value[0]/1000.}A voltage={mbs_value[1]}V power={mbs_value[2]}W]")
            except TypeError:
                logger.error(f"{the_cp.id}: Set GC MODBUS Device CP{the_cp.num} error!")

if __name__ == '__main__':
    asyncio.run(start())
