import asyncio
import logging

from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1, QOS_2

logger = logging.getLogger('test_sub')

my_config = {
    'keep_alive': 10,
    'ping_delay': 1,
    'default_qos': 0,
    'default_retain': False,
    'auto_reconnect': True,  # 开启自动重连
    'reconnect_max_interval': 90,  # 最大重试间隔 秒
    'reconnect_retries': 8,  # 一直重试，直到连上
}

C:MQTTClient = None
async def uptime_coro():
    # 创建客户端实例
    C = MQTTClient(client_id='test1', config=my_config, loop=None)
    await C.connect('mqtt://test.mosquitto.org/',
                    cleansession=True,
                    cafile=None,
                    extra_headers={})
    # 订阅 $SYS/broker/uptime'  QOS=1
    # 订阅 $SYS/broker/load/#'  QOS=2
    await C.subscribe([
        ('$SYS/broker/uptime', QOS_1),
        ('$SYS/broker/load/#', QOS_2),
    ])
    try:
        # 接收100条消息
        for i in range(0, 100):
            # 等待接收消息, 超时时间为None表示一直等待，返回message对象
            message = await C.deliver_message(timeout=None)
            packet = message.publish_packet
            print("%d:  %s => %s" % (i, packet.variable_header.topic_name,
                                     str(packet.payload.data)))
        # 取消订阅
        await C.unsubscribe(['$SYS/broker/uptime', '$SYS/broker/load/#'])
        # 客户端主动断开连接
        await C.disconnect()
    except ClientException as ce:
        logger.error("Client exception: %s" % ce)


if __name__ == '__main__':
    formatter = "[%(asctime)s] %(name)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=formatter)
    asyncio.get_event_loop().run_until_complete(uptime_coro())
    # asyncio.run(uptime_coro())
