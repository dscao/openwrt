"""OpenWrt Button Entities."""
import logging
from dataclasses import replace
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, BUTTON_TYPES, OpenWrtButtonEntityDescription
from .coordinator import OpenWrtDataUpdateCoordinator

# 初始化日志
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up buttons."""
    coordinator: OpenWrtDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # 获取当前路由器上实际存在的接口列表 (由 api.py 解析生成)
    available_interfaces = coordinator.data.get("_available_interfaces", [])
    
    entities = []
    
    for description in BUTTON_TYPES:
        # [核心逻辑] 如果是接口重连模板，则进行动态分裂
        if description.is_interface_template:
            if not available_interfaces:
                _LOGGER.debug("No available interfaces found, skipping dynamic buttons.")
                continue

            for iface in available_interfaces:
                # 动态生成新的 Description
                # 使用 dataclasses.replace 复制模板并修改特定字段
                new_desc = replace(
                    description,
                    key=f"reconnect_{iface}",                  # 生成唯一 Key: reconnect_wan
                    name=description.name.format(iface.upper()), # 格式化名称: Reconnect WAN
                    ubus_payload=iface,                        # 设置 Payload: wan
                    icon="mdi:lan-connect"                     # 你也可以根据接口名动态给不同图标
                )
                entities.append(OpenWrtButton(coordinator, new_desc))
        
        else:
            # 普通按钮直接添加
            entities.append(OpenWrtButton(coordinator, description))
        
    async_add_entities(entities)

class OpenWrtButton(ButtonEntity):
    """OpenWrt Button."""

    entity_description: OpenWrtButtonEntityDescription

    def __init__(
        self, 
        coordinator: OpenWrtDataUpdateCoordinator, 
        description: OpenWrtButtonEntityDescription
    ) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.api._host}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_has_entity_name = True

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info(f"OPENWRT BUTTON PRESSED: {self.name} (Key: {self.entity_description.key})")
        
        try:
            # 模式 A: 旧式 URL 请求
            if self.entity_description.url_path:
                _LOGGER.debug(f"Action Type: Legacy URL -> {self.entity_description.url_path}")
                await self.coordinator.api.execute_legacy_url_action(
                    self.entity_description.url_path
                )
                _LOGGER.info(f"Button action executed successfully (Legacy): {self.name}")
                
            # 模式 B: 高效 UBUS 模式
            elif self.entity_description.ubus_method:
                _LOGGER.debug(f"Action Type: UBUS -> Method: {self.entity_description.ubus_method}, Payload: {self.entity_description.ubus_payload}")
                await self.coordinator.api.execute_ubus_action(
                    self.entity_description.ubus_method,
                    self.entity_description.ubus_payload
                )
                _LOGGER.info(f"Button action executed successfully (UBUS): {self.name}")
                
            else:
                _LOGGER.warning(f"Button {self.name} has no valid action configuration!")

        except Exception as e:
            _LOGGER.error(f"Failed to execute button press for {self.name}: {e}", exc_info=True)