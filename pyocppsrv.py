import asyncio
import logging
import time
from datetime import datetime, timedelta
import json
from ocpp.routing import on
from ocpp.routing import after
from ocpp.v16 import enums
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call
from ocpp.v16 import call_result
from config import g_cp_config, g_connector, g_task_duration_disable

# Init Log
logger = logging.getLogger('psn')
logging.getLogger('ocpp').setLevel(level=logging.WARNING)
# logging.getLogger('ocpp').addHandler(logging.StreamHandler())


class Connector(object):
    def __init__(self, charge_point, connector_id):
        self.charge_point: ChargePoint = charge_point
        self.connector_id: int = connector_id
        self.transaction_id = self.connector_id
        self.meter_value_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') + "Z"
        self.meter_value_current = 0  # ocpp unit mA
        self.meter_value_voltage = 0  # ocpp unit V
        self.meter_value_current_L2 = 0  # ocpp unit mA
        self.meter_value_voltage_L2 = 0  # ocpp unit V
        self.meter_value_current_L3 = 0  # ocpp unit mA
        self.meter_value_voltage_L3 = 0  # ocpp unit V
        self.meter_value_energy = 0  # ocpp unit Wh
        self.meter_value_soc = 0  # ocpp unit Percent
        self.meter_value_power = 0  # ocpp unit W
        self.power_rate = 0
        self.remote_control = 0
        self.err_code = ""
        self.is_charing = False
        self.cp_status = ""
        self.max_current = 32  # unit A
        self.current_limit = self.max_current  # unit A
        self.current_limit_default = self.max_current  # unit A
        self.power_limit = 7000  # unit W
        self.power_limit_default = 7000  # unit W
        self.dev_id = 0
        self.charge_point_id = self.charge_point.id
        self.id = f"{self.charge_point_id}-{self.connector_id}"
        self.last_StartTransaction_uuid = ""
        self.last_set_power_rate_value = 0 # from MBX set power rate
        self.last_set_power_rate_time = 0 # record time of last send power rate to cp
        self.last_udp_send_report_time = 0 # record time of last send udp report to master box

        the_cp_config = g_cp_config.get(self.charge_point_id)
        if the_cp_config:
            self.charge_point.task_duration_disable = the_cp_config.get("task_duration_disable", False)
            self.charge_point.max_power = the_cp_config.get("max_power", 7000)  # max power is 7000W
            self.charge_point.charge_type = the_cp_config.get("charge_type", 1)  # 1:AC 2:DC
            self.charge_point.txprofile_phase2_start_period = the_cp_config.get("txprofile_phase2_start_period", 180)  # txprofile schdule - phase2
            self.charge_point.txprofile_phase2_limit = the_cp_config.get("txprofile_phase2_limit", 0)  # txprofile schdule - phase2
            self.charge_point.charge_dc_voltage = the_cp_config.get("charge_dc_voltage", 220)  # txprofile schdule - phase2
            self.charge_point.charge_dc_efficiency = the_cp_config.get("charge_dc_efficiency", 0.97)  # txprofile schdule - phase2
            self.charge_point.set_charging_profile_disable = the_cp_config.get("set_charging_profile_disable", False)
            self.power_limit = self.power_limit_default = self.charge_point.max_power
            dev_id_list = the_cp_config.get("dev_id_list")
            if isinstance(dev_id_list, list):
                if self.connector_id <= len(dev_id_list):
                    self.dev_id = dev_id_list[self.connector_id-1]

        g_connector[self.id] = self

    def isOnline(self):
        return self.charge_point.connect_status

    async def set_current_limit(self, current_limit: int):
        # if current_limit > 0:
        if current_limit >= 0:
            response = await self.charge_point.Set_Charging_Profile(enums.ChargingProfilePurposeType.tx_profile, current_limit, self.connector_id, self.transaction_id)
            if response and response.status == enums.ChargingProfileStatus.accepted:
                logger.debug(f"set_current_limit = {current_limit}")
                self.current_limit = current_limit
                return True
        return False

    async def set_current_limit_default(self, current_limit_default: int):
        # if current_limit_default > 0:
        if current_limit_default >= 0:
            response = await self.charge_point.Set_Charging_Profile(enums.ChargingProfilePurposeType.tx_default_profile, current_limit_default, self.connector_id, self.transaction_id)
            if response.status == enums.ChargingProfileStatus.accepted:
                self.current_limit_default = current_limit_default
                return True
        return False

    async def set_power_limit(self, power_limit: int):
        if power_limit >= 0:
            response = await self.charge_point.Set_Charging_Profile(enums.ChargingProfilePurposeType.tx_profile, power_limit, self.connector_id, self.transaction_id)
            if response and response.status == enums.ChargingProfileStatus.accepted:
                logger.debug(f"set_power_limit = {power_limit}")
                self.power_limit = power_limit
                return True
        return False

    async def set_power_limit_default(self, power_limit_default: int):
        # if power_limit_default > 0:
        if power_limit_default >= 0:
            response = await self.charge_point.Set_Charging_Profile(enums.ChargingProfilePurposeType.tx_default_profile, power_limit_default, self.connector_id, self.transaction_id)
            if response.status == enums.ChargingProfileStatus.accepted:
                self.power_limit_default = power_limit_default
                return True
        return False

    async def set_power_rate(self, power_rate):
        response = None 
        if power_rate >= 0:
            if self.charge_point.charge_type == 1:  # AC
                current_limit = int(power_rate * self.max_current / 100)
                if current_limit < 6:
                    current_limit = 0
                    logger.info(f'{self.id}: set current limit = 0A if limit < 6A')

                if self.is_charing:
                    response = await self.set_current_limit(current_limit)
                else:
                    response = await self.set_current_limit_default(current_limit)
            elif self.charge_point.charge_type == 2:  # DC
                power_limit = int(power_rate * self.charge_point.max_power / 100)
                if power_limit < 2000:
                    power_limit = 0
                    logger.info(f'{self.id}: set power limit = 0W if limit < 2000W')
                if self.is_charing:
                    response = await self.set_power_limit(power_limit)
                else:
                    response = await self.set_power_limit_default(power_limit)
            if response:
                self.power_rate = power_rate
                return True
        return False

    async def remote_start(self):
        self.remote_control = 1  # RemoteStartInitiated
        limit_default = self.current_limit_default
        if self.charge_point.charge_type == 2:  # DC
            limit_default = self.power_limit_default
        response = await self.charge_point.Remote_Start_Transaction(self.connector_id, limit_default, self.transaction_id)  # Start CP
        if response and response.status == enums.RemoteStartStopStatus.accepted:
            self.is_charing = True
            self.remote_control = 3  # RemoteStartAccepted
            return True
        else:
            self.remote_control = 2  # RemoteStartRejected
            return False

    async def remote_stop(self):
        self.remote_control = 5  # RemoteStopInitiated
        response = await self.charge_point.Remote_Stop_Transaction(self.transaction_id)  # Stop CP
        if response and response.status == enums.RemoteStartStopStatus.accepted:
            self.is_charing = False
            self.remote_control = 7  # RemoteStopAccepted
            return True
        else:
            self.remote_control = 6  # RemoteStopReject
            return False

    def print_info(self):
        logger.info(f"{self.id}\tdevId:{self.dev_id}\tpowerRate:{self.power_rate}%\tcurrent:{self.meter_value_current/1000.}A\tcurrentLimit:{self.current_limit}A currentLimitDefault:{self.current_limit_default}A\tstatus:{self.cp_status}")

    def get_report(self):
        return {"cpId": self.charge_point.id,
                "connectorId": self.connector_id,
                "devId": self.dev_id,
                "status": self.cp_status,
                "current": self.meter_value_current,
                "voltage": self.meter_value_voltage,
                "currentL2": self.meter_value_current_L2,
                "voltageL2": self.meter_value_voltage_L2,
                "currentL3": self.meter_value_current_L3,
                "voltageL3": self.meter_value_voltage_L3,
                "energy": self.meter_value_energy,
                "power": self.meter_value_power,
                "soc": self.meter_value_soc,
                "powerRate": self.power_rate,
                "currentLimit": self.current_limit,
                "currentLimitDefault": self.current_limit_default,
                "powerLimit": self.power_limit,
                "powerLimitDefault": self.power_limit_default,
                "meterValueSampleInterval": self.charge_point.meterValueSampleInterval,
                "firmware": self.charge_point.firmware_version,
                "chargerType": self.charge_point.charge_type,  # 1:AC 2:DC
                "phase": 1,  # 1/3
                "connectorNum": 1,
                "maxPower": self.charge_point.max_power,  # unit-W
                "maxCurrent": self.max_current,
                "remoteControl": self.remote_control,
                "errCode": self.err_code,
                # "timestamp":datetime.utcnow(),
                }

    async def trigger_status_notification(self):
        return await self.charge_point.trigger_status_notification(self.connector_id)

    async def trigger_meter_values(self):
        return await self.charge_point.trigger_meter_values(self.connector_id)


class ChargePoint(cp):
    # charge point instance with all the possible functions
    def __init__(self, id, connection):
        cp.__init__(self, id=id, connection=connection, response_timeout=10)
        self.websocket = connection
        self.connect_status = True
        self.id_tag = '1'
        self.firmware_version = ""
        self.connector = {}
        self.get_connector(1)
        self._unique_id_generator = self.get_uuid  # change to short uuid# 奥能的桩不能接收太长的UUID，如果在UUID前面加上PSN前缀
        self.meterValueSampleInterval = 0
        self.task_duration_disable = False
        self.max_power = 7000  # AC unit-W
        self.charge_type = 1  # 1:AC 2:DC
        self.txprofile_phase2_start_period = 180
        self.txprofile_phase2_limit = 0
        self.charge_dc_voltage =  220
        self.charge_dc_efficiency = 0.97
        self.set_charging_profile_disable = False

        logger.info(f'{self.id}: Init.')

    def get_connector(self, connector_id=1):
        if not connector_id:
            connector_id = 1
        connector = self.connector.get(connector_id)
        if not connector:
            connector = self.connector[connector_id] = Connector(self, connector_id)  # create connector object
        return connector

    def get_uuid(self):
        return str(int(round(time.time()*1000)))

    async def close(self):
        logger.info(f'{self.id}: close the websocket connection.')
        await self.websocket.close()

    @on(enums.Action.BootNotification)
    # on reciving boot message we reply with cueent time, heartbeat interval and accepted
    def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        if("firmware_version" in kwargs):
            self.firmware_version = kwargs["firmware_version"]
        self.connect_status = True
        logger.debug(f'{self.id}: On BootNotification model={charge_point_model} vendor={charge_point_vendor}.')
        # asyncio.create_task(self.trigger_status_notification())
        asyncio.create_task(self.set_config())
        asyncio.create_task(self.get_config())
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat()[:-3]+'Z',
            interval=300,
            status=enums.RegistrationStatus.accepted
        )

    # # Added for testing , can be removed in final version. If any new command to be tested , add them here
    # # After boot message is received we send multiple commands to see the charge point response
    # @after(enums.Action.BootNotification)
    # async def after_Boot_notification(self, **kwargs):
    #     logger.debug(f'{self.id}: After BootNotification')
    #     await asyncio.sleep(10)
    #     # await self.trigger_status_notification()   # Try to get StatusNotification,

    # This will not be received if we configure local authorization is true in charger

    @on(enums.Action.Authorize)
    def on_Authorize(self, id_tag, **kwargs):
        logger.debug(f'{self.id}: On Authorize id_tag={id_tag} kwargs={kwargs}.')
        self.id_tag = id_tag
        return call_result.AuthorizePayload(id_tag_info={"status": enums.AuthorizationStatus.accepted})

    # Charger initiates this command before starting the charging, transaction id is used from config file.Same need to be used for stop request.
    @on(enums.Action.StartTransaction)
    def on_start_transaction(self, connector_id, id_tag, meter_start, **kwargs):
        logger.info(f'{self.id}: On StartTransaction {connector_id}, {id_tag}, {meter_start} kwargs={kwargs}.')
        the_connector: Connector = self.get_connector(connector_id)
        return call_result.StartTransactionPayload(the_connector.transaction_id, id_tag_info={"status": enums.RemoteStartStopStatus.accepted})

    # Acknowledge the stop transaction
    @on(enums.Action.StopTransaction)
    def on_stop_transaction(self, **kwargs):
        logger.info(f'{self.id}: On StopTransaction kwargs={kwargs}.')
        return call_result.StopTransactionPayload()

    # Heartbeat response with current time in ISO8601 format
    @on(enums.Action.Heartbeat)
    async def on_HeartBeat(self, **kwargs):
        self.connect_status = True
        return call_result.HeartbeatPayload(current_time=str(datetime.utcnow().isoformat()[:-3]+'Z'))

    # Acknowledgemnt for Status notification
    @on(enums.Action.StatusNotification)
    async def on_status_notification(self, connector_id, error_code, status, **kwargs):
        the_connector: Connector = self.get_connector(connector_id)
        the_connector.cp_status = status
        the_connector.is_charing = (the_connector.cp_status in [enums.ChargePointStatus.charging, enums.ChargePointStatus.suspended_ev, enums.ChargePointStatus.suspended_evse, enums.ChargePointStatus.faulted])
        from task_udp import udp_send_report
        await udp_send_report(the_connector)  # callback
        if the_connector.cp_status == enums.ChargePointStatus.finishing:
            the_connector.meter_value_current = 0
            the_connector.meter_value_power = 0
            asyncio.create_task(self.trigger_meter_values(connector_id))
            logger.info(f"{self.id} set metervalue is 0 when status change to finishing")
        return call_result.StatusNotificationPayload()

    # Meter Values from the charger, we can use this info to understand the current feedback
    @on(enums.Action.MeterValues)
    def on_MeterValues(self, connector_id, **kwargs):
        try:
            the_connector: Connector = self.get_connector(connector_id)
            if the_connector:
                transactionId = kwargs.get('transaction_id')
                if transactionId:
                    the_connector.transaction_id = transactionId
                    logger.info(f"{self.id}-{transactionId} from MeterValues get transactionId is {transactionId}")
                meter_value_list = kwargs.get('meter_value')
                if isinstance(meter_value_list, list):
                    for meter_value in meter_value_list:
                        if(isinstance(meter_value, dict)):
                            the_connector.meter_value_timestamp = meter_value.get('timestamp')
                            sampled_value_list = meter_value.get('sampled_value')
                            if(isinstance(sampled_value_list, list)):
                                for sampled_value in sampled_value_list:
                                    if(isinstance(sampled_value, dict)):
                                        measurand = sampled_value.get('measurand')
                                        phase = sampled_value.get('phase', "L1")
                                        value = int(float(sampled_value.get('value')))
                                        if(measurand == enums.Measurand.current_import):  # Current.Import A
                                            if phase == "L1":
                                                the_connector.meter_value_current = value * 1000  # unit A->mA
                                            elif phase == "L2":
                                                the_connector.meter_value_current_L2 = value * 1000  # unit A->mA
                                            elif phase == "L3":
                                                the_connector.meter_value_current_L3 = value * 1000  # unit A->mA
                                        elif(measurand == enums.Measurand.voltage):  # Voltage V
                                            if phase == "L1":
                                                the_connector.meter_value_voltage = value  # unit V
                                            elif phase == "L2":
                                                the_connector.meter_value_voltage_L2 = value  # unit V
                                            elif phase == "L3":
                                                the_connector.meter_value_voltage_L3 = value  # unit V
                                        elif(measurand == enums.Measurand.energy_active_import_register):  # Energy.Active.Import.Register Wh
                                            the_connector.meter_value_energy = value  # unit Wh
                                        elif(measurand == enums.Measurand.soc):  # SoC Percent
                                            the_connector.meter_value_soc = value  # unit Percent
                                        elif(measurand == enums.Measurand.power_active_import):  # Power.Active.Import W
                                            the_connector.meter_value_power = value  # unit W
                
                #recalc current for DC charge
                if self.charge_type == 2 and the_connector.meter_value_power and self.charge_dc_voltage and self.charge_dc_efficiency:
                    the_connector.meter_value_voltage = self.charge_dc_voltage
                    the_connector.meter_value_current = 1000*int(the_connector.meter_value_power / 3 / self.charge_dc_voltage / self.charge_dc_efficiency) # A->mA
                    logger.info(f"{self.id}-{transactionId} recalculate current for DC charge, current = {the_connector.meter_value_current}A")
        except Exception as e:
            logger.error(f'{self.id}: parse meter value err!' + repr(e))

        return call_result.MeterValuesPayload()

    async def Change_Availability(self):
        """
        Request messages from Central to Charger
        Function to change the availability of charger to oerative/inoperative
        """
        request = call.ChangeAvailabilityPayload(
            connector_id=1,
            type=enums.AvailabilityType.operative
        )
        response = await self.call(request)
        print(response.status)

    async def Resetreq(self):
        request = call.ResetPayload(
            type=enums.ResetType.soft
        )
        response = await self.call(request)
        print(response.status)

    # Available but not suggested to use without understanding the impact, it will clear all the profiles
    async def Clear_Charging_Profiles(self):
        request = call.ClearChargingProfilePayload()
        response = await self.call(request)
        print(response.status)

    # If central wants to know some info we can initiate trigger message for charger to send particular messgae
    async def Trigger_Message(self, trigger_message, connector_id=1):
        logger.debug(f'{self.id}: Trigger Message {trigger_message}')
        response = await self.call(call.TriggerMessagePayload(
            connector_id=connector_id,
            requested_message=trigger_message
        ))
        return response

    # async def get_composite_schedule_status(self):
    #     response = await self.call(call.GetCompositeSchedulePayload(
    #         connector_id=1,
    #         duration=3600,
    #         charging_rate_unit=enums.ChargingRateUnitType.amps
    #     ))
    #     return response

    # @on(enums.Action.GetCompositeSchedule)
    # def on_GetCompositeSchedule(self, **kwargs):
    #     logger.info(f'{self.id}: On on_GetCompositeSchedule kwargs={kwargs}.')
    #     return call_result.GetCompositeSchedulePayload(enums.GetCompositeScheduleStatus.accepted)

    # Get CP StatusNotification
    async def trigger_status_notification(self, connector_id=1):
        return await self.Trigger_Message(enums.MessageTrigger.status_notification, connector_id)

    async def trigger_meter_values(self, connector_id=1):
        return await self.Trigger_Message(enums.MessageTrigger.meter_values, connector_id)

    async def Change_Configuration(self):
        request = call.ChangeConfigurationPayload(
            key='AuthorizeRemoteTxRequests',
            value='True'
        )
        response = await self.call(request)
        print(response.status)

    # Available and it may be needed in different models where we need to unlock after the transaction
    async def Unlock_Connector(self, connecterid):
        request = call.UnlockConnectorPayload(
            connector_id=connecterid
        )
        response = await self.call(request)
        print(response.status)

    async def Remote_Start_Transaction(self, connector_id=1, current_limit=32, transaction_id=1):
        # Request for remote start of charging session
        response = await self.call(call.RemoteStartTransactionPayload(
            id_tag=self.id_tag,
            connector_id=connector_id,
            # ,chargingUnit='Min' # Non-standard OCPP
            # ,chargingTarget=10
            charging_profile=self.get_charging_profile_payload(enums.ChargingProfilePurposeType.tx_profile, current_limit, transaction_id, connector_id)
        ))
        return response

    async def Remote_Stop_Transaction(self, transaction_id=1):
        # Remote request to stop the charging transaction
        response = await self.call(call.RemoteStopTransactionPayload(transaction_id))
        return response

    def get_charging_profile_payload(self, txprofile, currentlimit, transaction_id=1, connector_id=1):
        now = (datetime.utcnow() - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%S') + "Z"
        cs_charging_profiles = {
            "charging_profile_id": connector_id, # use connector id write to chargingProfileId
            "stack_level": 0,
            # "charging_profile_purpose": txprofile,
            "charging_profile_purpose": enums.ChargingProfilePurposeType.tx_default_profile,
            "charging_profile_kind": enums.ChargingProfileKindType.recurring,
            "recurrency_kind": enums.RecurrencyKind.daily,
            "charging_schedule": {
                "duration": 86400,  # AaoNeng need
                "startSchedule": now,  # AaoNeng need
                "charging_rate_unit": enums.ChargingRateUnitType.amps if self.charge_type == 1 else enums.ChargingRateUnitType.watts,
                "charging_schedule_period": [
                    {
                        "start_period": 0,
                        "limit": currentlimit,
                        "numberPhases": 1 #start charge don't suuport  numberPhases 3
                    }],
                #   "minChargingRate": 6  #Schneider does not support
            }
        }

        # if txprofile == enums.ChargingProfilePurposeType.tx_profile:
        cs_charging_profiles["transaction_id"] = transaction_id
        cs_charging_profiles["charging_schedule"]["charging_schedule_period"].append({
                "start_period": self.txprofile_phase2_start_period,
                "limit": self.txprofile_phase2_limit,
                "numberPhases": 1
                })

        return cs_charging_profiles

    async def Set_Charging_Profile(self, txprofile=enums.ChargingProfilePurposeType.tx_profile, currentlimit=32, connector_id=1, transaction_id=1):
        response = await self.call(call.SetChargingProfilePayload(
            connector_id=connector_id,
            cs_charging_profiles=self.get_charging_profile_payload(txprofile, currentlimit, transaction_id, connector_id)))
        return response

    async def update_firmware(self, location):
        logger.info(
            f'{self.id}: Start update_firmware location={location}')
        response = await self.call(call.UpdateFirmwarePayload(location=location, retrieve_date=datetime.utcnow().isoformat()[:-3]+'Z'))
        return response

    @on(enums.Action.FirmwareStatusNotification)
    def on_firmware_status_notification(self, **kwargs):
        logger.debug(
            f'{self.id}: On FirmwareStatusNotification kwargs={kwargs}.')
        return call_result.FirmwareStatusNotificationPayload()

    async def set_qrcode(self, location):
        logger.info(
            f'{self.id}: Start set qrcode location={location}')
        response = await self.call(call.DataTransferPayload(vendor_id="[QR]", message_id="SET", data=location))
        return response

    @on(enums.Action.DataTransfer)
    def on_data_transfer(self, **kwargs):
        logger.debug(
            f'{self.id}: On DataTransfer kwargs={kwargs}.')
        return call_result.DataTransferPayload(status=enums.DataTransferStatus.accepted)

    async def send_debug(self):
        logger.debug(
            f'{self.id}: Start send debug command')
        response = await self.call(call.DataTransferPayload(vendor_id="[DEBUG]", message_id="vipvalue"))
        return response

    async def get_config(self):
        # Setting is a dict with 3 keys: key, value and readonly.
        # See section 7.29 in https://github.com/mobilityhouse/ocpp/blob/master/docs/v16/ocpp-1.6.pdf
        logger.debug(f'{self.id}: send GetConfigurationPayload')
        response = await self.call(call.GetConfigurationPayload())
        if response:
            for setting in response.configuration_key:
                if setting['key'] == 'MeterValueSampleInterval':
                    self.meterValueSampleInterval = int(setting['value'])
                    logger.info(f"{self.id}: get meterValueSampleInterval = {self.meterValueSampleInterval}")
        return response

    async def set_config(self, key="MeterValueSampleInterval", value="10"):
        logger.info(f'{self.id}: send ChangeConfigurationPayload')
        response = await self.call(call.ChangeConfigurationPayload("MeterValueSampleInterval", value))
        return response
    
    async def clear_charging_profile(self):
        logger.info(f'{self.id}: send ClearChargingProfile')
        response = await self.call(call.ClearChargingProfilePayload())
        return response
