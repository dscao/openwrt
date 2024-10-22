"""OPENWRT Entities"""
import logging
import time
import datetime
import re
import requests
from async_timeout import timeout
from aiohttp.client_exceptions import ClientConnectorError
from bs4 import BeautifulSoup

from homeassistant.helpers.device_registry import DeviceEntryType

from homeassistant.components.button import ButtonEntity

from .const import (
    COORDINATOR, 
    DOMAIN, 
    BUTTON_TYPES, 
    CONF_HOST, 
    CONF_USERNAME, 
    CONF_PASSWD, 
    DO_URL,
    DO_URL2,
)

from .data_fetcher import DataFetcher

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add bjtoon_health_code entities from a config_entry."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    host = config_entry.data[CONF_HOST]
    username = config_entry.data[CONF_USERNAME]
    passwd = config_entry.data[CONF_PASSWD]

    buttons = []
    for button in BUTTON_TYPES:
        buttons.append(OPENWRTButton(hass, button, coordinator, host, username, passwd))

    async_add_entities(buttons, False)


class OPENWRTButton(ButtonEntity):
    """Define an bjtoon_health_code entity."""
    _attr_has_entity_name = True

    def __init__(self, hass, kind, coordinator, host, username, passwd):
        """Initialize."""
        super().__init__()
        self.kind = kind
        self.coordinator = coordinator
        self._state = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.coordinator.host)},
            "name": self.coordinator.data["device_name"],
            "manufacturer": "OpenWrt",
            "model": self.coordinator.data["model"],
            "sw_version": self.coordinator.data["sw_version"],
        }
        self._attr_device_class = "restart"
        self._attr_entity_registry_enabled_default = True
        self._hass = hass
        self._token = ""
        self._token_expire_time = 0
        self._allow_login = True
        self._fetcher = DataFetcher(hass, host, username, passwd)
        self._host = host
        
        
    async def get_access_token(self):
        if time.time() < self._token_expire_time:
            return self._token
        else:
            if self._allow_login == True:
                self._token = await self._fetcher._login_openwrt()
                if self._token == 403:
                    self._allow_login = False
                self._token_expire_time = time.time() + 60*60*2        
                return self._token

    @property
    def name(self):
        """Return the name."""
        return f"{BUTTON_TYPES[self.kind]['name']}"

    @property
    def unique_id(self):
        return f"{DOMAIN}_{self.kind}_{self.coordinator.host}"
        
    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return True

    @property
    def state(self):
        """Return the state."""
        return self._state

        
    @property
    def device_class(self):
        """Return the unit_of_measurement."""
        if BUTTON_TYPES[self.kind].get("device_class"):
            return BUTTON_TYPES[self.kind]["device_class"]
        
    @property
    def state_attributes(self): 
        attrs = {}
        data = self.coordinator.data
        if self.coordinator.data.get(self.kind + "_attrs"):
            attrs = self.coordinator.data[self.kind + "_attrs"]
        if data:            
            attrs["querytime"] = data["querytime"]        
        return attrs  
        
        
    def press(self) -> None:
        """Handle the button press."""

    async def async_press(self) -> None:
        """Handle the button press."""        
        await self._openwrt_action(BUTTON_TYPES[self.kind]["action"])

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update entity."""
        #await self.coordinator.async_request_refresh()        
        
        
    def requestpost_data(self, url, headerstr, datastr):
        responsedata = requests.post(url, headers=headerstr, data = datastr, verify=False, allow_redirects=False)
        if responsedata.status_code != 200:
            return responsedata.status_code
        #_LOGGER.debug(responsedata)
        return responsedata
        
    def requestget_data_text(self, url, headerstr):
        responsedata = requests.get(url, headers=headerstr)
        if responsedata.status_code != 200:
            return responsedata.status_code
        resdata = responsedata.content.decode('utf-8')
        return resdata
        
    async def _openwrt_action(self, action): 
        if self._allow_login == True:
            body = "token={{token}}&_=0.7647894831805453"
            contenttype = "application/x-www-form-urlencoded"
            sysauth = await self.get_access_token()
            header = {
                "Cookie": "sysauth=" + sysauth + ";sysauth_http=" + sysauth
            } 

            if action == "restart":
                parameter1 = "/admin/system/reboot"       
                parameter2 = "/admin/system/reboot/call" 
                
            elif action == "reconnect_iface":
                parameter1 = "admin/network/network"
                parameter2 = "admin/network/iface_reconnect/" + BUTTON_TYPES[self.kind]["iface"]
            elif action == "submit_data":
                parameter1 = BUTTON_TYPES[self.kind]["parameter1"]
                parameter2 = BUTTON_TYPES[self.kind]["parameter2"]
                body = BUTTON_TYPES[self.kind]["body"]
            
            url =  self._host + DO_URL + parameter1
            try:
                async with timeout(10): 
                    resdata = await self._hass.async_add_executor_job(self.requestget_data_text, url, header)
            except (
                ClientConnectorError
            ) as error:
                raise UpdateFailed(error)
            _LOGGER.debug("Requests remaining: %s", url)
            _LOGGER.debug(resdata)
            
            if resdata == 401 or resdata == 403:
                self._data = 401
                return
            try:
                soup = BeautifulSoup(resdata, 'html.parser')
                form_inputs = soup.find_all('input')
                form_data = {}
                for input_tag in form_inputs:
                    name = input_tag.get('name')
                    value = input_tag.get('value')
                    if name:
                        if value != "删除所有订阅节点" and value != "删除已订阅的节点" and value != "手动订阅" and value != "删除" and value != "添加" and value != "保存&应用":
                            form_data[name] = value
            except: 
                _LOGGER.debug("解析表单内容失败")
                    
            resdata = resdata.replace("\n","").replace("\r","")
            action_tokena = re.findall(r"token: '(.+?)' ", str(resdata))
            action_tokenb = re.findall(r"name=\"token\" value=\"(.+?)\"", str(resdata))
            #_LOGGER.debug( action_tokena)
            #_LOGGER.debug( action_tokenb)
            if len(action_tokena)>0:            
                action_token = action_tokena[0]
            elif len(action_tokenb)>0:
                action_token = action_tokenb[0]
            else:
                await self._openwrt_action2(action)
                return
            _LOGGER.debug("action_token: %s ", action_token) 

            if action == "submit_data":                
                body = form_data or {}
                body["token"] = action_token
            else:
                body = body.replace("{{token}}", action_token)
                
            header = {
                "Cookie": "sysauth=" + sysauth + ";sysauth_http=" + sysauth,
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
                "Content-type": str(contenttype),
                "Host": self._host.replace("http://","").replace("https://",""),
                "Origin": self._host,
                "Referer": url,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"

            }            
            url =  self._host + DO_URL + parameter2
            _LOGGER.debug(url)
            _LOGGER.debug(body)
            try:
                async with timeout(10): 
                    resdata = await self._hass.async_add_executor_job(self.requestpost_data, url, header, body)
            except (
                ClientConnectorError
            ) as error:
                raise UpdateFailed(error)
            _LOGGER.debug("Requests remaining: %s", url)
            _LOGGER.debug(resdata)
            if resdata == 401 or resdata == 403:
                self._data = 401
                return        
                    
        self._state = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _LOGGER.info("操作openwrt: %s ", url)    
        return "OK"
        
    async def _openwrt_action2(self, action): 
        if action == "submit_data":
            return
        if self._allow_login == True:
            url =  self._host + DO_URL2 + "?" + str(int(time.time() * 1000))
            sysauth = await self.get_access_token()          
            header = {"content-type":"application/json"}
            if action == "restart":
                body = body = '[{"jsonrpc":"2.0","id":1,"method":"call","params":["'+sysauth+'","params":["'+sysauth+'","system","reboot",{}]}]'
            elif action == "reconnect_iface":
                body = '[{"jsonrpc":"2.0","id":1,"method":"call","params":["'+sysauth+'","file","exec",{"command":"/sbin/ifup","params":["'+BUTTON_TYPES[self.kind]["iface"]+'"],"env":null}]}]'
            _LOGGER.debug(url)
            _LOGGER.debug(body)
            try:
                async with timeout(10): 
                    resdata = await self._hass.async_add_executor_job(self.requestpost_data, url, header, body)
            except (
                ClientConnectorError
            ) as error:
                raise UpdateFailed(error)
            _LOGGER.debug("Requests remaining: %s", url)
            _LOGGER.debug(resdata)
            if resdata == 401 or resdata == 403:
                self._data = 401
                return
        self._state = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _LOGGER.info("操作openwrt: %s ", url)    
        return "OK"
        
