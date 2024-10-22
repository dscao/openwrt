"""
get openwrt info by token and sysauth
"""

import logging
import requests
import re
import asyncio
import json
import time
import datetime
from urllib import parse

from async_timeout import timeout
from aiohttp.client_exceptions import ClientConnectorError
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from .const import (
    DO_URL,
    DO_URL2,
)

_LOGGER = logging.getLogger(__name__)



class DataFetcher:
    """fetch the openwrt data"""

    def __init__(self, hass, host, username, passwd):

        self._host = host
        self._username = username
        self._passwd = passwd
        self._hass = hass
        self._session_client = async_create_clientsession(hass)
        self._data = {}
    
    def requestget_data(self, url, headerstr):
        responsedata = requests.get(url, headers=headerstr)
        if responsedata.status_code != 200:
            return responsedata.status_code
        json_text = responsedata.content.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata
        
    def requestpost_data(self, url, headerstr, datastr):
        responsedata = requests.post(url, headers=headerstr, data = datastr, verify=False)
        if responsedata.status_code != 200:
            return responsedata.status_code
        json_text = responsedata.content.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata
        
    def requestget_data_text(self, url, headerstr, datastr):
        responsedata = requests.post(url, headers=headerstr, verify=False)
        if responsedata.status_code != 200:
            return responsedata.status_code
        resdata = responsedata.content.decode('utf-8')
        return resdata
        
    def requestpost_json(self, url, headerstr, json_body):
        responsedata = requests.post(url, headers=headerstr, json = json_body, verify=False)
        if responsedata.status_code != 200:
            return responsedata.status_code
        json_text = responsedata.content.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata

    def requestpost_cookies(self, url, headerstr, body):
        responsedata = requests.post(url, headers=headerstr, data = body, verify=False, allow_redirects=False)
        if responsedata.status_code == 403:            
            return 403
        if responsedata.status_code != 200 and responsedata.status_code != 302:
            return responsedata.status_code        
        resdata = responsedata.cookies.get("sysauth") or responsedata.cookies.get("sysauth_http") or responsedata.cookies.get("sysauth_https")
        return resdata         
        
    async def _login_openwrt(self):
        hass = self._hass
        host = self._host
        username =self._username
        passwd =self._passwd
        header = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        body = "luci_username=" + username + "&luci_password=" + passwd
        url =  host + DO_URL
        _LOGGER.debug("Requests remaining: %s", url)          
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.requestpost_cookies, url, header, body) 
                if resdata ==403:
                    _LOGGER.debug("OPENWRT Username or Password is wrong，please reconfig!")
                    return resdata
                else:                   
                    _LOGGER.debug("login_successfully for OPENWRT")
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)       
        return resdata
        
    
    def seconds_to_dhms(self, seconds):
        if isinstance(seconds,str):
            return seconds.replace("\n%","")
        days = seconds // (3600 * 24)
        hours = (seconds // 3600) % 24
        minutes = (seconds // 60) % 60
        seconds = seconds % 60
        if days > 0 :
            return ("{0}天{1}小时{2}分钟".format(days,hours,minutes))
        if hours > 0 :
            return ("{0}小时{1}分钟".format(hours,minutes))
        if minutes > 0 :
            return ("{0}分钟{1}秒".format(minutes,seconds))
        return ("{0}秒".format(seconds)) 
        

    async def _get_openwrt_status(self, sysauth):
        header = {
            "Cookie": "sysauth=" + sysauth
        }
        
        parameter = "?status=1"
        
        body = ""

        url =  self._host + DO_URL + parameter
        _LOGGER.debug("Requests remaining: %s", url)
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.requestget_data, url, header)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        
        _LOGGER.debug(resdata)
        if resdata == 401 or resdata == 403:
            self._data = 401
            return        
        
        # resdata["cpuinfo"] = " 1795.377 MHz    +20.0°C  (crit = +100.0°C) \n" 
        self._data = {}
        if resdata.get("cpuinfo"):
            cpuinfo = resdata["cpuinfo"]
        elif resdata.get("cpuwd"):
            cpuinfo = resdata["cpuwd"]
        else:
            cpuinfo = ""
        cputemp = re.findall(r"\+(.+?)°C",cpuinfo)
         
        #_LOGGER.debug(cputemp)
        if cputemp:
            if isinstance(cputemp,list):
                self._data["openwrt_cputemp"] = cputemp[0]
        else:
            self._data["openwrt_cputemp"] = 0
        
        try:
            self._data["openwrt_uptime"] = self.seconds_to_dhms(resdata["uptime"])
        except Exception:
            self._data["openwrt_uptime"] = resdata["uptime"]
        self._data["openwrt_cpu"] = resdata["cpuusage"].replace("\n%","")
        self._data["openwrt_memory"] = round((1 - resdata["memory"]["available"]/resdata["memory"]["total"])*100,0)
        self._data["openwrt_memory_attrs"] = resdata["memory"]
        self._data["openwrt_conncount"] = resdata["conncount"]
        if resdata.get("userinfo"):
            self._data["openwrt_user_online"] = resdata["userinfo"].replace("\n","")
        else:
            self._data["openwrt_user_online"] = ""
        
        if resdata.get("wan"):
            self._data["openwrt_wan_ip"] = resdata["wan"]["ipaddr"]
            self._data["openwrt_wan_ip_attrs"] = resdata["wan"]            
            try:
                self._data["openwrt_wan_uptime"] = self.seconds_to_dhms(resdata["wan"]["uptime"]) 
            except Exception:
                self._data["openwrt_wan_uptime"] = resdata["wan"]["uptime"]
        else:
            self._data["openwrt_wan_ip"] = ""
            self._data["openwrt_wan_uptime"] = ""
        if resdata.get("wan6"):
            self._data["openwrt_wan6_ip"] = resdata["wan6"]["ip6addr"]
            self._data["openwrt_wan6_ip_attrs"] = resdata["wan6"]
            try:
                self._data["openwrt_wan6_uptime"] = self.seconds_to_dhms(resdata["wan6"]["uptime"]) 
            except Exception:
                self._data["openwrt_wan6_uptime"] = resdata["wan6"]["uptime"]
        else:
            self._data["openwrt_wan6_ip"] = ""
            self._data["openwrt_wan6_uptime"] = ""    
        
        querytime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._data["querytime"] = querytime

        return
        
    async def _get_openwrt_status2(self, sysauth):
        body = '[{"jsonrpc":"2.0","id":2,"method":"call","params":["'+sysauth+'","system","info",{}]},{"jsonrpc":"2.0","id":4,"method":"call","params":["'+sysauth+'","luci","getCPUUsage",{}]},{"jsonrpc":"2.0","id":5,"method":"call","params":["'+sysauth+'","luci","getTempInfo",{}]},{"jsonrpc":"2.0","id":6,"method":"call","params":["'+sysauth+'","luci","getOnlineUsers",{}]},{"jsonrpc":"2.0","id":7,"method":"call","params":["'+sysauth+'","file","read",{"path": "/proc/sys/net/netfilter/nf_conntrack_count"}]},{"jsonrpc":"2.0","id":8,"method":"call","params":["'+sysauth+'","network.interface","dump",{}]}]'
        url =  self._host + DO_URL2 + "?" + str(int(time.time() * 1000))
        _LOGGER.debug("Requests remaining: %s", url)    
        _LOGGER.debug(body)
        header = {"content-type":"application/json"}
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.requestpost_data, url, header, body)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _LOGGER.debug(resdata)
        if resdata == 401 or resdata == 403:
            self._data = 401
            return
        
        self._data = {}

        cpuinfo = resdata[1]["result"][1]["cpuusage"]
        try:
            cputemp = resdata[2]["result"][1]["cputemp"]
        except:
            cputemp = 0
        self._data["openwrt_cputemp"] = cputemp
        
        systeminfo = resdata[0]["result"][1]
        useronlineinfo = resdata[3]["result"]
        conncountinfo = resdata[4]["result"]
        networkinfo = resdata[5]["result"]

        try:
            self._data["openwrt_uptime"] = self.seconds_to_dhms(systeminfo["uptime"])
        except Exception:
            self._data["openwrt_uptime"] = systeminfo["uptime"]
        self._data["openwrt_cpu"] = cpuinfo.replace("%","")
        self._data["openwrt_memory"] = round((1 - systeminfo["memory"]["available"]/systeminfo["memory"]["total"])*100,0)
        self._data["openwrt_memory_attrs"] = systeminfo["memory"]

        if len(useronlineinfo)>1:
            self._data["openwrt_user_online"] = useronlineinfo[1]["onlineusers"]
        else:
            self._data["openwrt_user_online"] = ""
        if len(conncountinfo)>1:
            self._data["openwrt_conncount"] = conncountinfo[1]["data"].replace("\n","")
        else:
            self._data["openwrt_conncount"] = ""
        _LOGGER.debug(networkinfo) 
        self._data["openwrt_wan_ip"] = ""
        self._data["openwrt_wan_uptime"] = ""
        self._data["openwrt_wan6_ip"] = ""
        self._data["openwrt_wan6_uptime"] = ""
        if len(networkinfo)>1:
            for interface in networkinfo[1]["interface"]:
                if interface["interface"].lower() == 'wan':
                    ipv4_addresses = interface['ipv4-address']
                    if len(ipv4_addresses) > 0:
                        self._data["openwrt_wan_ip"] = ipv4_addresses[0]['address']
                        self._data["openwrt_wan_uptime"] = interface['uptime']
                        try:
                            self._data["openwrt_wan_uptime"] = self.seconds_to_dhms(interface['uptime'])
                        except Exception:
                            self._data["openwrt_wan_uptime"] = interface['uptime']
                elif interface['interface'].lower() == 'wan6':
                    ipv6_addresses = interface['ipv6-address']
                    if len(ipv6_addresses) > 0:
                        self._data["openwrt_wan6_ip"] = ipv6_addresses[0]['address']
                        try:
                            self._data["openwrt_wan6_uptime"] = self.seconds_to_dhms(interface['uptime'])
                        except Exception:
                            self._data["openwrt_wan6_uptime"] = interface['uptime']

        querytime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._data["querytime"] = querytime

        return
  
    async def _get_openwrt_version(self, sysauth):
        header = {
            "Cookie": "sysauth=" + sysauth
        }
             
        body = ""
        url =  self._host + DO_URL + "admin/status/overview"
        _LOGGER.debug("Requests remaining: %s", url)
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.requestget_data_text, url, header, body)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        #_LOGGER.debug(resdata)
        if resdata == 401 or resdata == 403:
            self._data = 401
            return
        openwrtinfo = {}
        resdata = resdata.replace("\n","").replace("\r","")
        try:
            openwrtinfo["sw_version"] = re.findall(r"内核版本</td><td>(.+?)</td>", str(resdata))
        except Exception:
            openwrtinfo["sw_version"] = ""
        try:
            openwrtinfo["device_name"] = re.findall(r"<meta name=\"application-name\" content=\"(.+?) - LuCI", resdata)[0]
        except Exception:
            openwrtinfo["device_name"] = "Openwrt"
        try:
            openwrtinfo["model"] = re.findall(r"固件版本</td><td>(.+?)</td>", resdata)
        except Exception:
            openwrtinfo["model"] = ""

        return openwrtinfo
    async def _get_openwrt_version2(self, sysauth):
        
        #body = {"jsonrpc":"2.0","id":"init","method":"list"}
        body = '[{"jsonrpc":"2.0","id":1,"method":"call","params":["'+sysauth+'","system","board",{}]}]'
        url =  self._host + DO_URL2 + "?" + str(int(time.time() * 1000))
        _LOGGER.debug("Requests remaining: %s", url)    
        _LOGGER.debug(body)
        header = {"content-type":"application/json"}
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.requestpost_data, url, header, body)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _LOGGER.debug(resdata)
        if resdata == 401 or resdata == 403:
            self._data = 401
            return
        openwrtinfo = {}
        openwrtinfo["sw_version"] = resdata[0]["result"][1]["kernel"]
        openwrtinfo["device_name"] = resdata[0]["result"][1]["hostname"]
        openwrtinfo["model"] = resdata[0]["result"][1]["release"]["revision"]
        return openwrtinfo
        
        
    async def get_data(self, sysauth):  
        tasks = [
            asyncio.create_task(self._get_openwrt_status(sysauth)),
        ]
        await asyncio.gather(*tasks)
                    
        return self._data
        
    async def get_data2(self, sysauth):  
        tasks = [
            asyncio.create_task(self._get_openwrt_status2(sysauth)),
        ]
        await asyncio.gather(*tasks)
                    
        return self._data


class GetDataError(Exception):
    """request error or response data is unexpected"""
