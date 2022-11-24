"""Constants for the openwrt health code integration."""

DOMAIN = "openwrt"

######### CONF KEY
CONF_USERNAME = "username"
CONF_PASSWD = "passwd"
CONF_HOST = "host"
CONF_TOKEN_EXPIRE_TIME = "token_expire_time"
COORDINATOR = "coordinator"
CONF_UPDATE_INTERVAL = "update_interval_seconds"

UNDO_UPDATE_LISTENER = "undo_update_listener"

##### OPENWRT URL
DO_URL = "/cgi-bin/luci/"


### Sensor Configuration

SENSOR_TYPES = {
    "openwrt_uptime": {
        "icon": "mdi:clock-time-eight",
        "label": "OpenWrt启动时长",
        "name": "openwrt_uptime",
    },
     "openwrt_cpu": {
        "icon": "mdi:cpu-64-bit",
        "label": "CPU占用",
        "name": "openwrt_cpu",
        "unit_of_measurement": "%",
    },
     "openwrt_cputemp": {
        "icon": "mdi:thermometer",
        "label": "CPU温度",
        "name": "openwrt_cputemp",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
    },
    "openwrt_memory": {
        "icon": "mdi:memory",
        "label": "内存占用",
        "name": "openwrt_memory",
        "unit_of_measurement": "%",
    },   
    "openwrt_wan_ip": {
        "icon": "mdi:wan",
        "label": "WAN IP",
        "name": "openwrt_wan_ip",
    },
    "openwrt_wan_uptime": {
        "icon": "mdi:timer-sync-outline",
        "label": "WAN Uptime",
        "name": "openwrt_wan_uptime",
    },
    "openwrt_wan6_ip": {
        "icon": "mdi:wan",
        "label": "WAN IP6",
        "name": "openwrt_wan6_ip",
    },
    "openwrt_wan6_uptime": {
        "icon": "mdi:timer-sync-outline",
        "label": "WAN IP6 Uptime",
        "name": "openwrt_wan6_uptime",
    },
    # "openwrt_total_up": {
        # "icon": "mdi:upload-network",
        # "label": "上传总量",
        # "name": "openwrt_totalup",
        # "unit_of_measurement": "GB",
    # },
    # "openwrt_total_down": {
        # "icon": "mdi:download-network",
        # "label": "下载总量",
        # "name": "openwrt_totaldown",
        # "unit_of_measurement": "GB",
    # },     
    # "openwrt_upload": {
        # "icon": "mdi:wifi-arrow-up",
        # "label": "上传速度",
        # "name": "openwrt_upload",
        # "unit_of_measurement": "MB/s",
    # },
    # "openwrt_download": {
        # "icon": "mdi:wifi-arrow-down",
        # "label": "下载速度",
        # "name": "openwrt_download",
        # "unit_of_measurement": "MB/s",
    # },
}

 
BUTTON_TYPES = {
    "openwrt_restart": {
        "label": "OpenWrt重启",
        "name": "openwrt_restart",
        "device_class": "restart",
        "action": "restart",
    },
    "openwrt_restart_reconnect_wan": {
        "label": "OpenWrt重连wan网络",
        "name": "openwrt_reconnect_wan",
        "device_class": "restart",
        "action": "reconnect_iface",
        "iface": "wan", 
    },
    "openwrt_restart_reconnect_gw": {
        "label": "OpenWrt重连GW网络",
        "name": "openwrt_reconnect_gw", #实体名称
        "device_class": "restart",
        "action": "reconnect_iface",
        "iface": "gw",  #网络接口
    },
    "openwrt_restart_reconnect_docker": {
        "label": "OpenWrt重连docker网络",
        "name": "openwrt_reconnect_docker",
        "device_class": "restart",
        "action": "reconnect_iface",
        "iface": "docker", 
    },
    "openwrt_node_subscribe": {
        "label": "OpenWrt重新订阅fq节点",
        "name": "openwrt_node_subscribe",
        "device_class": "restart",
        "action": "submit_data",
        "parameter1": "admin/services/passwall/node_subscribe", 
        "parameter2": "admin/services/passwall/node_subscribe", 
        "body": {
            "token": "action_token}}",
            "cbi.submit": "1",
            "cbi.cbe.passwall.cfg08b7d7.subscribe_proxy": "1",
            "cbid.passwall.cfg08b7d7.filter_keyword_mode": "1",
            "cbid.passwall.cfg08b7d7.filter_discard_list": "s801",
            "cbid.passwall.cfg08b7d7.filter_discard_list": "剩余流量",
            "cbid.passwall.cfg08b7d7.filter_discard_list": "QQ群",
            "cbid.passwall.cfg08b7d7.filter_discard_list": "官网",
            "cbid.passwall.cfg08b7d7.filter_keep_list": "",
            "cbid.passwall.cfg08b7d7.ss_aead_type": "xray",
            "cbid.passwall.cfg08b7d7.trojan_type": "trojan-plus",
            "cbi.sts.passwall.subscribe_list": "",
            "cbid.passwall.cfg108b02.remark": "SS",
            "cbid.passwall.cfg108b02.url": "填写节点订阅地址", #此处可填写自己的订阅地址
            "cbid.passwall.cfg108b02._update": "手动订阅"
            }
    }
}