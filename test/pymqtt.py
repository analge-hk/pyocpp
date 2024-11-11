import logging
import paho.mqtt.client as mqtt
import _thread
import time

# 封装 paho-mqtt
# Init Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MQTT')


class mqttHandle():
    def __init__(self, host, port, username, password, project_id, on_mqtt_message, sub_topics):
        self.client = None
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.project_id = project_id
        self.connected = False
        self.subscribed = False
        self.on_mqtt_message = on_mqtt_message
        self.sub_topics = sub_topics

    def on_connect(self, client, userdata, flags, rc):
        if rc == mqtt.CONNACK_ACCEPTED:
            logger.debug('on_connect Connection successful.')
            self.connected = True

            # 订阅MQTT消息
            for topic in self.sub_topics:
                self.client.subscribe(topic)
                logger.info(f"mqtt subscribe {topic}")
        else:
            logger.debug(f'on_connect Connection refused. rc={rc}')
            client.disconnect()

    def on_disconnect(self, client, userdata, rc):
        if(rc == mqtt.MQTT_ERR_SUCCESS):
            self.connected = False
            logger.debug(f"on_disconnect rc:{rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.subscribed = True
        logger.debug(f"on_subscribe msgId={mid} qos = {granted_qos}")

    def on_publish(self, client, userdata, mid):
        logger.debug(f"on_publish msgId={mid}")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")
        logger.debug(
            f"on_message userdata:{userdata} qos:{msg.qos} topic:{msg.topic} payload:{str(payload)}")
        self.on_mqtt_message(msg.topic, payload)

    def on_log(self, client, obj, level, string):
        pass

    def publish(self, topic="", payload="", qos=0):
        if(self.connected):
            payload_bytes = payload.encode("utf-8")
            messageInfo = self.client.publish(
                topic, payload_bytes, qos)  # send msg
            # print(messageInfo.rc, messageInfo.mid)
            return messageInfo.rc == 0

    def run_loop(self):
        self.client = mqtt.Client(client_id="")  # random clientid

        # call back
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish

        # mqtt library log
        # self.client.enable_logger(logger)
        # self.client.on_log = self.on_log

        # connect param
        self.client.user_data_set("user")
        self.client.username_pw_set(self.username, self.password)
        self.client.connect(host=self.host, port=self.port, keepalive=60)

        # run start
        self.client.loop_forever()  # mqtt run
        logger.debug("loop stop")

    def run_stop(self):
        logger.debug("call run_stop")
        self.client.disconnect()
        self.client = None

def on_mqtt_message_test(topic: str, payload: str):
    print(topic, payload)
    mqttc.publish("PI/OCPP/UP/test", str)


if __name__ == '__main__':
    mqttc = mqttHandle(host="open.nala.net.cn", port=1883, username="pi", password="", project_id=8, on_mqtt_message=on_mqtt_message_test,
        sub_topics=["PI/OCPP/DOWN/#"])  # create new mqtt client object
    mqttc.run_loop()

    # # create new mqtt thread and run start
    # _thread.start_new_thread(mqttc.run_loop, ())

    # for i in range(3):
    #     time.sleep(1)
    #     mqttc.publish("PI/EVSE/8/", f'payload {i}')  # send msg

    # # time.sleep(60)
    # mqttc.run_stop()  # stop mqtt client
    # time.sleep(3)  # wait all end.
