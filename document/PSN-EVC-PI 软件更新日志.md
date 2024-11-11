# PSN-EVC-PI 软件更新日志

| 版本 | 发布日期   | 版本变更描述                                                 |
| ---- | ---------- | ------------------------------------------------------------ |
| v1   | 2021/04/08 | 基于Anu版本发布到松山湖和HKE进行测试                         |
| v2   | 2021/05/03 | 在 SetChargingProfile 时移除MinChargingRate 参数。<br/>Schneider充电桩不支持MinChargingRate参数。 |
| v3   | 2021/05/08 | 重构软件。<br/>主要解决程序状态和充电桩状态不一致导致的不可控问题。<br/>优化Modbus数据获取。<br/>增加OCPP命令响应10秒超时，当超的时候主动断开ws连接<br/>SetChargingProfile在非充电状态时发送tx_default_profile命令，在充电状态下发送tx_profile命令。<br/>ANACE1系列充电桩有时候对于tx_default_profile命令不响应。 |
| v4   | 2021/05/13 | 当server检测到WS连接断开时，不要主动断开WS连接，如果还能收到CP的心跳包就恢复连接。<br/>没有充电桩连接时不回写场景状态到NALA。<br/>SetChargingProfile电流设置为整数。Schneider发送SetChargingProfile命令不支持小数。 ANACE1在发送CompositeScheduleStatus命令不支持小数。 |
| v5   | 2021/05/21 | 在打印日志时中增加软件版本标签。<br/>增加手工命令行用于调试和升级CP。<br/>支持充电桩远程升级，启动，停止，设置电流上限，支持远程设置充电桩QR Code。<br/>增加远程启动同时SetChargingProfile，防止充电桩启动电流过大。<br/>对于ANACE1充电桩增加发送远程debug命令。 |
| v6   | 2021/5/28  | 收到充电桩BootNotification状态5s后主动询问充电桩当前状态<br/>只有充电桩有明确连接状态时才会回写NALA场景状态，充电桩断电、断网情况不回写NALA场景状态 |
| v7   | 2021/10/12 | 支持OCPP数据采样通过Modbus回写到GC的NALA设备,需要GC固件v0.37以上版本 |

