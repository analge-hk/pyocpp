
import json

json_str = '''
[2,"c58ea80f-ae39-5e02-88dd-6088fd730323","BootNotification",{"chargePointModel":"AC_Charger","chargePointVendor":"DELIGHT","chargePointSerialNumber":"458A9F9151E8BBD6","firmwareVersion":"OCPP1.6J-V1.13.3@Jul 13 2021"}]
'''
print(json_str)

# json_obj = json.loads(json_str)
# json_obj[3].pop("chargePointSerialNumber", None)
# if isinstance(json_obj, list) and len(json_obj)>2:
#     json_obj[1] = f"abc-{json_obj[1]}"

# print(json_obj[2])
# json_str = json.dumps(json_obj)
# print(json_str)


from ocpp.messages import pack, unpack, Call, CallResult, CallError
from ocpp.exceptions import OCPPError

msg = unpack(json_str)
if isinstance(msg, Call):
    call:Call = msg
    print("Call"+call.to_json())
    call.unique_id = "SS-"+call.unique_id
    newmsg = pack(msg)
    print(newmsg)

a = {"a":1}
print(a)

for i in a:
    print(i)

for i,j in a.items():
    print(i,j)

a = {"a":1, "b":None}
j = json.dumps(a, ensure_ascii=False)
print(a)