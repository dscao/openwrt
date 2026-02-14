"""Coordinator for OpenWrt."""
import logging
from datetime import timedelta
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN
from .api import OpenWrtApi, OpenWrtAuthError, OpenWrtConnectionError

_LOGGER = logging.getLogger(__name__)

class OpenWrtDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching OpenWrt data."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        api: OpenWrtApi, 
        update_interval: int
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_info = {}

    async def _async_update_data(self):
        """Update data via API."""
        try:
            # 设定超时保护，防止请求卡死
            async with async_timeout.timeout(15):
                data = await self.api.get_data()
                
                if data:
                    self.device_info = {
                        "identifiers": {(DOMAIN, self.api._host)},
                        "name": data.get("device_name", "OpenWrt Router"),
                        "manufacturer": "OpenWrt",
                        "model": data.get("device_model", "Router"),
                        "sw_version": data.get("sw_version"),
                        "configuration_url": self.api._host,
                    }
                return data

        except OpenWrtAuthError:
            # Token 过期或认证失败
            _LOGGER.debug("Authentication failed, trying to re-login...")
            # 尝试重新登录一次
            try:
                self.api._sysauth = None
                await self.api.login()
                # 重登录后立即重试获取数据
                return await self.api.get_data()
            except (OpenWrtAuthError, OpenWrtConnectionError) as err:
                # 如果重试依然失败，抛出 UpdateFailed
                # 这样 HA 会标记实体为“不可用”，并在下个周期自动重试
                raise UpdateFailed(f"Authentication failed: {err}") from err

        except OpenWrtConnectionError as err:
            # 网络连接错误（如路由器重启中）
            # 直接抛出 UpdateFailed，实体变“不可用”，等待路由器启动完成
            raise UpdateFailed(f"Connection error: {err}") from err
            
        except Exception as err:
            # 其他未知错误
            raise UpdateFailed(f"Unexpected error: {err}") from err