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
DO_URL2 = "/ubus/"

### Sensor Configuration

SENSOR_TYPES = {
    "openwrt_uptime": {
        "icon": "mdi:clock-time-eight",
        "label": "OpenWrt启动时长",
        "name": "Uptime",
    },
     "openwrt_cpu": {
        "icon": "mdi:cpu-64-bit",
        "label": "CPU占用",
        "name": "CPU",
        "unit_of_measurement": "%",
    },
     "openwrt_cputemp": {
        "icon": "mdi:thermometer",
        "label": "CPU温度",
        "name": "CPU_temperature",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
    },
    "openwrt_memory": {
        "icon": "mdi:memory",
        "label": "内存占用",
        "name": "Memory",
        "unit_of_measurement": "%",
    },   
    "openwrt_wan_ip": {
        "icon": "mdi:wan",
        "label": "WAN IP",
        "name": "Wan_ip",
    },
    "openwrt_wan_uptime": {
        "icon": "mdi:timer-sync-outline",
        "label": "WAN Uptime",
        "name": "Wan_uptime",
    },
    "openwrt_wan6_ip": {
        "icon": "mdi:wan",
        "label": "WAN IP6",
        "name": "Wan6_ip",
    },
    "openwrt_wan6_uptime": {
        "icon": "mdi:timer-sync-outline",
        "label": "WAN IP6 Uptime",
        "name": "Wan6_uptime",
    },
    "openwrt_user_online": {
        "icon": "mdi:account-multiple",
        "label": "在线用户数",
        "name": "User_online",
    },
    "openwrt_conncount": {
        "icon": "mdi:lan-connect",
        "label": "活动连接",
        "name": "Connect_count",
    },
    
}

 
BUTTON_TYPES = {
    "openwrt_restart": {
        "label": "OpenWrt重启",
        "name": "Restart",
        "device_class": "restart",
        "action": "restart",
    },
    "openwrt_restart_reconnect_wan": {
        "label": "OpenWrt重连wan网络",
        "name": "Reconnect_wan",
        "device_class": "restart",
        "action": "reconnect_iface",
        "iface": "wan", 
    },
    "openwrt_restart_reconnect_wan6": {
        "label": "OpenWrt重连wan6网络",
        "name": "Reconnect_wan6",
        "device_class": "restart",
        "action": "reconnect_iface",
        "iface": "wan6", 
    },
    "openwrt_restart_reconnect_gw": {
        "label": "OpenWrt重连GW网络",
        "name": "Reconnect_gw", #实体名称
        "device_class": "restart",
        "action": "reconnect_iface",
        "iface": "gw",  #网络接口
    },
    "openwrt_node_subscribe": {
        "label": "OpenWrt重新订阅fq节点",
        "name": "Node_subscribe",
        "device_class": "restart",
        "action": "submit_data",
        "parameter1": "admin/services/passwall/node_subscribe", 
        "parameter2": "admin/services/passwall/node_subscribe", 
        "body": {}
    }
}
