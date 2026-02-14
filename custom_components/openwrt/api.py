"""OpenWrt API Client."""
import logging
import asyncio
import json
import re
from urllib.parse import quote
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ClientError

_LOGGER = logging.getLogger(__name__)

class OpenWrtAuthError(Exception):
    """Authentication error."""

class OpenWrtConnectionError(Exception):
    """Connection error."""

class OpenWrtApi:
    """Async API Client for OpenWrt."""

    def __init__(
        self, 
        host: str, 
        username: str, 
        password: str, 
        session: aiohttp.ClientSession
    ) -> None:
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._session = session
        self._sysauth = None
        
    async def login(self) -> bool:
        """Login to OpenWrt and get sysauth cookie."""
        url = f"{self._host}/cgi-bin/luci/"
        payload = f"luci_username={self._username}&luci_password={quote(self._password)}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            async with self._session.post(
                url, 
                data=payload, 
                headers=headers, 
                ssl=False, 
                allow_redirects=False,
                timeout=10 # 增加超时限制
            ) as resp:
                
                if resp.status == 403:
                    # 密码错误，清除 token 并抛出认证错误
                    self._sysauth = None
                    raise OpenWrtAuthError("Invalid credentials")
                
                if resp.status not in (200, 302):
                    _LOGGER.warning(f"Login failed with status: {resp.status}")
                    return False

                target_cookies = ["sysauth", "sysauth_http", "sysauth_https"]
                for name in target_cookies:
                    if name in resp.cookies:
                        self._sysauth = resp.cookies[name].value
                        _LOGGER.debug("Login successful (Set-Cookie)")
                        return True
                for cookie in self._session.cookie_jar:
                    if cookie.key in target_cookies:
                        self._sysauth = cookie.value
                        _LOGGER.debug("Login successful (CookieJar)")
                        return True

        except ClientError as err:
            # 抛出连接错误，交给 Coordinator 处理
            raise OpenWrtConnectionError(f"Connection error during login: {err}")
        except asyncio.TimeoutError:
            raise OpenWrtConnectionError("Connection timed out during login")
        
        _LOGGER.warning("Login request accepted but no cookie found.")
        return False

    async def get_data(self) -> dict[str, Any]:
        """Fetch all data using UBUS (JSON-RPC)."""
        # 如果没有 token，尝试登录
        if not self._sysauth:
            if not await self.login():
                # 登录失败（非网络错误，可能是逻辑错误），抛出异常让 Coordinator 重试
                raise OpenWrtAuthError("Login failed")

        rpc_calls = [
            {"jsonrpc": "2.0", "id": 1, "method": "call", "params": [self._sysauth, "system", "info", {}]},
            {"jsonrpc": "2.0", "id": 2, "method": "call", "params": [self._sysauth, "system", "board", {}]},
            {"jsonrpc": "2.0", "id": 3, "method": "call", "params": [self._sysauth, "luci", "getCPUUsage", {}]},
            {"jsonrpc": "2.0", "id": 4, "method": "call", "params": [self._sysauth, "luci", "getTempInfo", {}]},
            {"jsonrpc": "2.0", "id": 5, "method": "call", "params": [self._sysauth, "luci", "getOnlineUsers", {}]},
            {"jsonrpc": "2.0", "id": 6, "method": "call", "params": [self._sysauth, "network.interface", "dump", {}]},
            {"jsonrpc": "2.0", "id": 7, "method": "call", "params": [self._sysauth, "file", "read", {"path": "/proc/sys/net/netfilter/nf_conntrack_count"}]},
            {"jsonrpc": "2.0", "id": 8, "method": "call", "params": [self._sysauth, "file", "read", {"path": "/sys/class/thermal/thermal_zone0/temp"}]}
        ]
        
        url = f"{self._host}/ubus/"
        try:
            async with self._session.post(url, json=rpc_calls, ssl=False, timeout=10) as resp:
                if resp.status in (401, 403):
                    # Token 过期
                    self._sysauth = None
                    raise OpenWrtAuthError("Token expired")
                
                try:
                    data = await resp.json()
                except Exception:
                    self._sysauth = None
                    raise OpenWrtConnectionError("Invalid JSON response")

                return self._parse_ubus_data(data)

        except ClientError as err:
            raise OpenWrtConnectionError(f"Connection error fetching data: {err}")
        except asyncio.TimeoutError:
            raise OpenWrtConnectionError("Timeout fetching data")

    def _parse_ubus_data(self, data: list) -> dict:
        """Parse ubus response list."""
        res = {}
        try:
            if not isinstance(data, list):
                return res

            # 1. System Info (ID 1)
            if len(data) > 0:
                sys_res = data[0].get("result")
                if sys_res and len(sys_res) > 1:
                    sys_info = sys_res[1]
                    res["openwrt_uptime"] = sys_info.get("uptime")
                    if mem := sys_info.get("memory"):
                        total = mem.get("total", 1)
                        free = mem.get("free", 0)
                        if total > 0:
                            res["openwrt_memory"] = round((1 - free / total) * 100, 0)

            # 2. System Board (ID 2) [新增解析]
            if len(data) > 1:
                board_res = data[1].get("result")
                if board_res and len(board_res) > 1:
                    board_info = board_res[1]
                    # 提取主机名
                    res["device_name"] = board_info.get("hostname", "OpenWrt")
                    # 提取型号
                    res["device_model"] = board_info.get("model", "Router")
                    # 提取固件版本 (release.description 包含完整版本号)
                    release = board_info.get("release", {})
                    res["sw_version"] = release.get("description", release.get("version"))

            # 3. CPU Usage
            if len(data) > 2:
                cpu_res = data[2].get("result")
                val = None
                if isinstance(cpu_res, dict): 
                     val = cpu_res.get("cpuusage")
                elif isinstance(cpu_res, list) and len(cpu_res) > 0:
                     item = cpu_res[1] if len(cpu_res) > 1 else cpu_res[0]
                     val = item.get("cpuusage") if isinstance(item, dict) else item
                
                if val is not None:
                    if isinstance(val, str):
                        try:
                            res["openwrt_cpu"] = float(val.replace("%", "").strip())
                        except ValueError:
                            res["openwrt_cpu"] = 0
                    else:
                        res["openwrt_cpu"] = val

            # 4 & 8. CPU Temp
            temp_val = 0
            if len(data) > 3:
                temp_res = data[3].get("result")
                if isinstance(temp_res, dict):
                    temp_val = temp_res.get("cputemp", 0)
                elif isinstance(temp_res, list) and len(temp_res) > 1:
                     temp_val = temp_res[1].get("cputemp", 0)
            
            if not temp_val and len(data) > 7:
                file_res = data[7].get("result")
                if file_res and len(file_res) > 1:
                    raw_temp = file_res[1].get("data", "").strip()
                    if raw_temp.isdigit():
                        temp_val = float(raw_temp) / 1000.0
            if temp_val:
                res["openwrt_cputemp"] = temp_val

            # 5. Online Users
            if len(data) > 4:
                user_res = data[4].get("result")
                if isinstance(user_res, list) and len(user_res) > 1:
                    res["openwrt_user_online"] = user_res[1].get("onlineusers")

            # 6. Network Dump
            if len(data) > 5:
                net_res = data[5].get("result")
                if net_res and len(net_res) > 1:
                    interfaces = net_res[1].get("interface", [])
                    available_interfaces = []
                    for iface in interfaces:
                        name = iface.get("interface", "").lower()
                        if not name or name == "loopback": continue
                        available_interfaces.append(name)
                        ipv4 = iface.get("ipv4-address", [])
                        if ipv4: res[f"openwrt_{name}_ip"] = ipv4[0].get("address")
                        ipv6 = iface.get("ipv6-address", [])
                        if ipv6: res[f"openwrt_{name}_ipv6"] = ipv6[0].get("address")
                        res[f"openwrt_{name}_uptime"] = iface.get("uptime")
                    res["_available_interfaces"] = available_interfaces

            # 7. Active Connections
            if len(data) > 6:
                conn_res = data[6].get("result")
                if conn_res and len(conn_res) > 1:
                    conn_str = conn_res[1].get("data", "").strip()
                    if conn_str.isdigit():
                        res["openwrt_conncount"] = int(conn_str)
        except Exception as e:
            _LOGGER.error(f"Error parsing ubus data: {e}")
        return res

    async def execute_legacy_url_action(self, url_path: str) -> None:
        """Legacy URL action."""
        if not self._sysauth:
            await self.login()
        full_url = f"{self._host}/cgi-bin/luci/{url_path}"
        token = None
        try:
            async with self._session.get(full_url, ssl=False) as resp:
                if resp.status in (401, 403):
                    self._sysauth = None
                    return
                text = await resp.text()
                if match := re.search(r"token:\s*'([a-f0-9]+)'", text):
                    token = match.group(1)
                elif match := re.search(r'name="token"\s+value="([a-f0-9]+)"', text):
                    token = match.group(1)
            if token:
                data = {"token": token}
                async with self._session.post(full_url, data=data, ssl=False) as resp:
                    pass
        except ClientError:
            pass

    async def execute_ubus_action(self, method: str, payload: Any = None) -> None:
        """Execute Ubus action."""
        if not self._sysauth:
            await self.login()
        
        object_path = ""
        func_name = ""
        params = {}

        if method == "system_reboot":
            object_path = "system"
            func_name = "reboot"
        elif method == "network_reconnect":
            # 使用 /sbin/ifup 强制重连接口
            object_path = "file"
            func_name = "exec"
            params = {"command": "/sbin/ifup", "params": [payload]}
        elif method == "exec_command":
            # 通用命令执行 (用于插件订阅更新等)
            # payload 格式: {"command": "/usr/bin/xxx", "params": ["arg1"]}
            object_path = "file"
            func_name = "exec"
            params = payload
        
        if object_path:
            body = {
                "jsonrpc": "2.0", "id": 1, "method": "call", 
                "params": [self._sysauth, object_path, func_name, params]
            }
            url = f"{self._host}/ubus/"
            try:
                async with self._session.post(url, json=body, ssl=False) as resp:
                    if resp.status in (401, 403):
                        self._sysauth = None
                        _LOGGER.warning("UBUS action failed: Token expired")
                    else:
                        _LOGGER.debug(f"UBUS action sent. Status: {resp.status}")
            except ClientError as e:
                _LOGGER.error(f"Failed to execute ubus action: {e}")