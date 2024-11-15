from pymodbus.client.sync import ModbusTcpClient
from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
import time
import asyncio
import logging
import config

g_modbus_client:ModbusTcpClient = None
g_is_current_overload = False
g_last_modbus_response_time = 0

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meter")

meter_config = config.config_file.get("meter")
if meter_config:
    ip = meter_config.get("ip")
    meter_type = meter_config.get("meter_type", 0) # 0:pri_meter 1:psn-meter
    slave_id = meter_config.get("slave_id", 1)
    port = meter_config.get("port", 5000)
    current_overload = meter_config.get("current_overload") # unit: A
    disconnect_timeout = meter_config.get("disconnect_timeout", 10) # 断网超时时间
    reg_start = meter_config.get("reg_start", 76) # 断网超时时间
    reg_count = meter_config.get("reg_count", 11) # 断网超时时间
    logger.info(f"Meter config {ip}:{port} meter_type:{meter_type} slave:{slave_id}current_overload:{current_overload} disconnect_timeout:{disconnect_timeout} reg_start:{reg_start} reg_count:{reg_count}")
else:
    g_is_current_overload = False

def modus_request():
# 获取modubs_tcp连接的modus meter，按S751E-G，IA,3相电流
# 成功：返回3个相位电流最大值
# 失败：返回 -1
    global g_modbus_client
    # 读取单个寄存器
    try:    
        if not g_modbus_client.connect():
            logger.warn(f"modbus tcp connect failed: {ip}:{port}")

        data = g_modbus_client._check_read_buffer()
        if data:
            # logger.warn(f"clear buffer: {len(data)}")
            pass

        if meter_type == 0:     # pri-meter
            response = g_modbus_client.read_holding_registers(address=reg_start, count=reg_count, unit=slave_id)
            if not response.isError():
                current_ma_L1 = response.registers[0] <<16 | response.registers[1] # big endian unit: ma
                current_ma_L2 = response.registers[2] <<16 | response.registers[3] # big endian unit: ma
                current_ma_L3 = response.registers[4] <<16 | response.registers[5] # big endian unit: ma
                current_ma_max = max(current_ma_L1, current_ma_L2, current_ma_L3) # unit mA
                current_max = current_ma_max/1000. # unit: A
                # logger.info(f"Meter S751E-G Ia_RMS(mA) Register : {response.registers} L1: ({current_ma_L1/1000.:.1f} A) L2: ({current_ma_L2/1000.:.1f} A) L3: ({current_ma_L3/1000.:.1f} A) max: ({current_ma_max/1000.:.1f} A)")
                return current_max
            else:
                logger.info("Failed to read meter registers")
                return -1
        elif meter_type == 1:     # psn-meter
            response = g_modbus_client.read_input_registers(address=reg_start, count=reg_count, unit=slave_id)
            if not response.isError():
                current_ma_L1 = response.registers[0] # 0.1A
                current_ma_L2 = response.registers[1] # 0.1A
                current_ma_L3 = response.registers[2] # 0.1A
                current_ma_max = max(current_ma_L1, current_ma_L2, current_ma_L3) # 0.1A
                if current_ma_max == 0:
                    return -1
                current_max = current_ma_max/10. # unit: A
                logger.info(f"Meter config {ip}:{port} meter_type:{meter_type} slave:{slave_id} current_overload:{current_overload} disconnect_timeout:{disconnect_timeout} reg_start:{reg_start} reg_count:{reg_count}")
                logger.info(f"PSN-Meter Register : {response.registers} L1: ({current_ma_L1/10.:.1f} A) L2: ({current_ma_L2/10.:.1f} A) L3: ({current_ma_L3/10.:.1f} A) max: ({current_ma_max/10.:.1f} A)")
                return current_max
            else:
                logger.info("Failed to read meter registers")
                return -1

    except Exception as e:
        logger.error(e)
        return -1

    # # 关闭连接
    # client.close()

async def modbus_loop():
    global g_modbus_client, g_is_current_overload, g_last_modbus_response_time
    # 创建Modbus TCP客户端
    g_modbus_client = ModbusTcpClient(ip, port=port, framer=ModbusFramer, timeout=1)
    if g_modbus_client.connect():
        logger.info(f"connect to {ip}:{port} success.")
    else:
        logger.error(f"connect to {ip}:{port} failed.")

    loop = asyncio.get_running_loop()

    while True:
        try:
            await asyncio.sleep(1)

            r = await loop.run_in_executor(None, modus_request)
            if r>=0:
                logger.info(f"get meter current = ({r:.1f} A)")
                g_last_modbus_response_time = time.time()
            else:
                logger.info("get meter current failed")
                
            elapsed_time = int(time.time() - g_last_modbus_response_time)    # 连续10秒没有获取meter数据，当超载处理
            if elapsed_time > disconnect_timeout:
                g_is_current_overload = True
                logger.warn(f"meter current overload, get meter value timeout ({elapsed_time} s)")
            elif r > current_overload:
                g_is_current_overload = True
                logger.warn(f"meter current overload, (meter_value: {r:.1f} A) > (overload_value: {current_overload} A)")
            elif r >= 0 and r < current_overload:
                g_is_current_overload = False
        except Exception as e:
            logger.error(e)
            return -1

async def start():
    # not config meter
    if not meter_config:
        logger.warn("meter not config")
        return
    
    while True:
        try:    
            await modbus_loop()
        except Exception as e:
            logger.error(e)

if __name__ == '__main__':
    asyncio.run(start())