"""Constants for the openwrt integration."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Final

from homeassistant.components.sensor import (
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)

DOMAIN: Final = "openwrt"

CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_UPDATE_INTERVAL: Final = "update_interval_seconds"

@dataclass
class OpenWrtSensorEntityDescription(SensorEntityDescription):
    """自定义 OpenWrt 传感器描述类"""
    json_key: str | None = None
    is_human_readable: bool = False
    is_interface_template: bool = False
    template_suffix: str | None = None # e.g. "_ip", "_ipv6", "_uptime"

@dataclass
class OpenWrtButtonEntityDescription(ButtonEntityDescription):
    """自定义 OpenWrt 按钮描述类"""
    url_path: str | None = None
    req_method: str = "POST" 
    ubus_method: str | None = None
    ubus_payload: str | dict | None = None
    is_interface_template: bool = False

# --- 传感器定义 ---
SENSOR_TYPES: tuple[OpenWrtSensorEntityDescription, ...] = (
    # 系统级传感器 (静态)
    OpenWrtSensorEntityDescription(
        key="uptime",
        json_key="openwrt_uptime",
        name="Uptime",
        icon="mdi:clock-time-eight",
        is_human_readable=True, 
    ),
    OpenWrtSensorEntityDescription(
        key="cpu_load",
        json_key="openwrt_cpu",
        name="CPU Load",
        icon="mdi:cpu-64-bit",
        unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenWrtSensorEntityDescription(
        key="cpu_temp",
        json_key="openwrt_cputemp",
        name="CPU Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenWrtSensorEntityDescription(
        key="memory_usage",
        json_key="openwrt_memory",
        name="Memory Usage",
        icon="mdi:memory",
        unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenWrtSensorEntityDescription(
        key="online_users",
        json_key="openwrt_user_online",
        name="Online Users",
        icon="mdi:account-multiple",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenWrtSensorEntityDescription(
        key="active_connections",
        json_key="openwrt_conncount",
        name="Active Connections",
        icon="mdi:lan-connect",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    
    # [核心修改] 接口动态传感器模板
    
    # 模板 1: 接口 IP
    OpenWrtSensorEntityDescription(
        key="interface_ip", # 占位符
        name="{} IP",       # 占位符，例如: WAN IP
        icon="mdi:ip-network",
        is_interface_template=True,
        template_suffix="_ip",
    ),
    
    # 模板 2: 接口 IPv6
    OpenWrtSensorEntityDescription(
        key="interface_ipv6",
        name="{} IPv6",
        icon="mdi:ip-network-outline",
        is_interface_template=True,
        template_suffix="_ipv6",
    ),
    
    # 模板 3: 接口在线时间
    OpenWrtSensorEntityDescription(
        key="interface_uptime",
        name="{} Uptime",
        icon="mdi:timer-sync-outline",
        is_human_readable=True,
        is_interface_template=True,
        template_suffix="_uptime",
    ),
)

# --- 按钮定义 ---
BUTTON_TYPES: tuple[OpenWrtButtonEntityDescription, ...] = (
    OpenWrtButtonEntityDescription(
        key="restart",
        name="Restart Router",
        icon="mdi:restart",
        device_class="restart",
        ubus_method="system_reboot",
    ),
    # 接口重连模板
    OpenWrtButtonEntityDescription(
        key="reconnect_interface",
        name="Reconnect {}",
        icon="mdi:lan-connect",
        ubus_method="network_reconnect",
        is_interface_template=True,
    ),
    # Passwall 订阅更新 (显式调用 lua 解释器) 无效果注释掉
    #OpenWrtButtonEntityDescription(
    #    key="node_subscribe_passwall",
    #    name="Passwall Update Subscribe",
    #    icon="mdi:update",
    #    ubus_method="exec_command",
    #    # command: /usr/bin/lua, params: [脚本路径, 参数]
    #    ubus_payload={
    #        "command": "/usr/bin/lua", 
    #        "params": ["/usr/share/passwall/subscribe.lua", "start", "cfg0fb7d7"]
    #    }
    #),
    
    # OpenClash 订阅更新 (显式调用 sh 解释器)
    OpenWrtButtonEntityDescription(
        key="node_subscribe_openclash",
        name="OpenClash Update Subscribe",
        icon="mdi:update",
        ubus_method="exec_command",
        # command: /bin/sh, params: [脚本路径, 参数]
        ubus_payload={
            "command": "/bin/sh", 
            "params": ["/usr/share/openclash/openclash.sh", "-s"]
        }
    ),
)
