"""OpenWrt Sensor Entities."""
from dataclasses import replace
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES, OpenWrtSensorEntityDescription
from .coordinator import OpenWrtDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors."""
    coordinator: OpenWrtDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # 获取接口列表
    available_interfaces = coordinator.data.get("_available_interfaces", [])
    
    entities = []
    
    for description in SENSOR_TYPES:
        
        # [逻辑 A] 接口动态模板传感器
        if description.is_interface_template:
            for iface in available_interfaces:
                # 动态生成 Key: openwrt_wan_ip
                dynamic_key = f"openwrt_{iface}{description.template_suffix}"
                
                # 预检查数据是否存在
                val = coordinator.data.get(dynamic_key)
                if val is not None and val != "":
                    # 动态生成 Description
                    new_desc = replace(
                        description,
                        key=dynamic_key,
                        json_key=dynamic_key, # json_key 与 key 一致
                        name=description.name.format(iface.upper()) # WAN IP
                    )
                    entities.append(OpenWrtSensor(coordinator, new_desc))
                    
        # [逻辑 B] 普通静态传感器
        else:
            key = description.json_key or description.key
            val = coordinator.data.get(key)
            
            if val is not None and val != "":
                entities.append(OpenWrtSensor(coordinator, description))
            
    async_add_entities(entities)

class OpenWrtSensor(CoordinatorEntity, SensorEntity):
    """Representation of an OpenWrt sensor."""

    entity_description: OpenWrtSensorEntityDescription

    def __init__(
        self, 
        coordinator: OpenWrtDataUpdateCoordinator, 
        description: OpenWrtSensorEntityDescription
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.api._host}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_has_entity_name = True
        
        if description.unit_of_measurement:
             self._attr_native_unit_of_measurement = description.unit_of_measurement
        
        if description.device_class:
            self._attr_device_class = description.device_class

    @property
    def available(self) -> bool:
        """运行时可用性检查"""
        if not super().available:
            return False
        key = self.entity_description.json_key or self.entity_description.key
        val = self.coordinator.data.get(key)
        return val is not None and val != ""

    @property
    def native_value(self):
        """Return the state of the sensor."""
        key = self.entity_description.json_key or self.entity_description.key
        val = self.coordinator.data.get(key)
        
        if val is None:
            return None

        # 如果是需要人类可读的（如 Uptime），转换为字符串
        if self.entity_description.is_human_readable:
            return self._seconds_to_human(val)

        # 针对 device_class 为 DURATION 的保护 (虽然我们现在主要用 human_readable)
        if self.device_class == SensorDeviceClass.DURATION:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        
        return val

    def _seconds_to_human(self, seconds) -> str:
        """将秒数转换为人类可读格式 (天/小时/分/秒)"""
        try:
            seconds = int(float(seconds))
        except (ValueError, TypeError):
            return "未知"

        if seconds < 60:
            return f"{seconds}秒"

        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分")
        # 仅在小于1分钟时显示秒，或者你可以去掉这个判断总是显示秒
        if days == 0 and hours == 0 and minutes == 0:
             parts.append(f"{seconds}秒")
            
        return "".join(parts)