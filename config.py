import json
from operator import truediv
from os import path

# Load config file
config_file = None
script_dir = path.dirname(__file__)
filepath = path.join(script_dir, "config.json")
with open(filepath, "r") as fp:
    config_file = json.load(fp)
print("Load config file ", filepath)


g_cp_config = config_file.get("cp")
g_cp_ocpp = {} #handle charge point object, id=10037
g_connector = {} #handle cp-connector,  id=10037-1
g_gc_ip = config_file.get("udp_server_host")