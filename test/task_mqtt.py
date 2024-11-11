import logging
import pymqtt
import _thread
import time
import config
from config import *
from pyocppsrv import ChargePoint
import asyncio

mqttc:pymqtt.mqttHandle = None

# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('task_mqtt')

MQTT_PUB_TOPIC_PI_OCPP_UP:str = "PI/OCPP/UP/"       #ocpp payload 上传
MQTT_SUB_TOPIC_PI_OCPP_DOWN:str = "PI/OCPP/DOWN/"   #ocpp payload 下发
MQTT_PUB_TOPIC_PI_CMD_UP:str = "PI/CMD/UP/"        #cmd payload 上传
MQTT_SUB_TOPIC_PI_CMD_DOWN:str = "PI/CMD/DOWN/"    #cmd payload 下发


#发送MQTT消息
def mqtt_send(topic:str, payload:str):
    global mqttc
    if(mqttc==None):
        return
    mqttc.client.publish(topic, payload)
    logger.info("send topic:%s, paylod:%s", topic, payload)

def mqtt_send_pi_ocpp_up(charge_point_id:str, ocpp_payload:str):
    mqtt_send(MQTT_PUB_TOPIC_PI_OCPP_UP+charge_point_id, ocpp_payload)

def mqtt_send_pi_cmd_up(charge_point_id:str, pi_cmd:dict):
    json_str = json.dumps(pi_cmd)
    mqtt_send(MQTT_PUB_TOPIC_PI_CMD_UP+charge_point_id, json_str)

# 接收MQTT消息
def on_mqtt_message(topic:str, payload:str):
    logger.info(f"mqtt recv topic:{topic} payload:{payload}")

    #parse cpid
    topic_split = topic.split('/')
    if len(topic_split)>3:
        charge_point_id = topic_split[3]

    if topic.startswith(MQTT_SUB_TOPIC_PI_OCPP_DOWN):
        try:
            if charge_point_id in g_ws:
                logger.info("send payload to:" + charge_point_id)
                # await g_ws[charge_point_id].send(payload)

        except Exception as e:
            logger.error("send payload: "+ repr(e))
    elif topic.startswith(MQTT_SUB_TOPIC_PI_CMD_DOWN):
        try:
            if charge_point_id in g_cp_ocpp:
                cp = g_cp_ocpp.get(charge_point_id)
                if(isinstance(cp, ChargePoint) and cp.connect_status == True):
                    pi_cmd = json.loads(payload)
                    method = pi_cmd.get("method")
                    logger.info(f"{charge_point_id} recv pi cmd {method}")
                    if (method == "start"):
                        cp.transaction_id_next = pi_cmd.get("transactionId")
                        # response = await cp.Remote_Start_Transaction()
                        # response = asyncio.run(cp.Remote_Start_Transaction())
                        if config.g_run_loop != None:
                            response = config.g_run_loop.run_until_complete(cp.Remote_Start_Transaction())
                            pi_cmd["response"] = response.status
                            mqtt_send_pi_cmd_up(charge_point_id, pi_cmd)
                    elif (method == "stop"):
                        # response = await cp.Remote_Stop_Transaction()
                        # response = asyncio.run(cp.Remote_Stop_Transaction())
                        if config.g_run_loop != None:
                            response = config.g_run_loop.run_until_complete(cp.Remote_Stop_Transaction())
                        pi_cmd["response"] = response.status
                        mqtt_send_pi_cmd_up(charge_point_id, pi_cmd)
                    else:
                        logger.error("unknow pi cmd! %s", method)
        except Exception as e:
            logger.error("send payload: "+ repr(e))

def start():
    global mqttc
    logging.basicConfig(level=logging.INFO)
    mqtt_sub_topics = []
    for i in range(CP_count):
        charge_point_id = CP_list[i]['id']
        mqtt_sub_topics.append(MQTT_SUB_TOPIC_PI_OCPP_DOWN + charge_point_id)
        mqtt_sub_topics.append(MQTT_SUB_TOPIC_PI_CMD_DOWN + charge_point_id)
        
    mqttc = pymqtt.mqttHandle(host="open.nala.net.cn", port=1883, username="pi", password="", project_id=8, on_mqtt_message=on_mqtt_message,sub_topics=mqtt_sub_topics)  # create new mqtt client object
    mqttc.run_loop()

if __name__ == '__main__':
    # formatter = "[%(asctime)s] %(name)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    # logging.basicConfig(level=logging.DEBUG, format=formatter)
    
    # create new mqtt thread and run start
    _thread.start_new_thread(start, ())
    print("finish")
    while True:
        mqtt_send_pi_ocpp_up("000080003", "test123")
        time.sleep(1)
