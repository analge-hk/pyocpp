import asyncio
import logging
from config import *
from pyocppsrv import  Connector
from config import g_task_duration_disable, g_masterbox_disconnect_timeout
import time
from task_udp import udp_send_report
import task_modbus_async
import task_udp
from ocpp.v16 import enums

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("duration")

async def start():
    while True:
        try:
            await asyncio.sleep(1)
            for connector in g_connector.values():
                the_connector:Connector = connector

                if not the_connector.isOnline():
                    continue
    
                if the_connector.charge_point.set_charging_profile_disable:
                    the_connector.power_rate = the_connector.last_set_power_rate_value # don't send charging profile command
                    continue
        
                # set charge profile command min interval
                elapsed_time = int(time.time() - the_connector.last_set_power_rate_time)

                # logger.info(f'{the_connector.id}: elapsed_time={elapsed_time} last_set_power_rate_value={the_connector.last_set_power_rate_value} power_rate={the_connector.power_rate}')
        
                if the_connector.last_set_power_rate_value == the_connector.power_rate:
                    if g_task_duration_disable:
                        # logger.info(f'{the_connector.id}: passed g_task_duration_disable')
                        continue
                    if the_connector.charge_point.task_duration_disable: 
                        # logger.info(f'{the_connector.id}: passed task_duration_disable')
                        continue
                    if not the_connector.is_charing: # only txprofile
                        # logger.info(f'{the_connector.id}: passed is_charing')
                        continue
                    if elapsed_time < 1:
                        # logger.info(f'{the_connector.id}: 45s')
                        continue
                    if the_connector.is_charing and elapsed_time < 2:
                        continue
                    logger.info(f'{the_connector.id}: Reset duration={the_connector.charge_point.txprofile_phase2_start_period} every 1 seconds')
                else:
                    if the_connector.charge_point.charge_type == 1 and elapsed_time < 1:  # AC
                        # logger.info(f'{the_connector.id}: set current limit interval of the AC-CP must be greater than 10 seconds')
                        continue
                    if the_connector.charge_point.charge_type == 2 and elapsed_time < 1:  # DC
                        # logger.info(f'{the_connector.id}: The set power limit interval of the DC-CP must be greater than 20s')
                        continue   
        
                try:
                    # When the TCP meter is overloaded, all charging stations are shut down
                    if task_modbus_async.g_is_current_overload:
                        the_connector.last_set_power_rate_value = 1
                        the_connector.cp_status = enums.ChargePointStatus.available
                        logger.warn("meter overload, set power_rate = 1, set status available")
                            
                    # when master-box offline
                    elapsed_time = int(time.time() - task_udp.g_last_recv_master_time)
                    if elapsed_time > g_masterbox_disconnect_timeout:
                        the_connector.last_set_power_rate_value = 1
                        the_connector.cp_status = enums.ChargePointStatus.available
                        logger.warn(f"master box offline timeout ({elapsed_time} s) > ({g_masterbox_disconnect_timeout} s), last_recv_time: ({task_udp.g_last_recv_master_time}s), set power_rate = 1, set status available")

                    the_connector.last_set_power_rate_time = time.time() # update request time
                    await the_connector.set_power_rate(the_connector.last_set_power_rate_value)
                    await udp_send_report(the_connector)  # send udp message PI->MBX
                    await asyncio.sleep(.1)
                except Exception as e:
                    logger.error(repr(e))

                # for the_cp in g_cp_ocpp.values():
                #     try:
                #         await the_cp.trigger_meter_values()
                #         await the_cp.get_config() # Not all Charging station support it
                #         await the_cp.set_config() # Not all Charging station support it
                #     except Exception as e:
                #         logger.error(repr(e))
        except Exception as e:
            logger.error(repr(e))
                            
if __name__ == '__main__':
    asyncio.run(start())
