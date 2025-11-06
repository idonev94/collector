import json
import os
from typing import List
import aiohttp

from assurance.base.http import HttpClient

from .templats import (
    GET_DEVICES,
    GET_DEVICE_STATS,
    GET_FAILOVER_STATUS,
    GET_LICENSE,
    GET_STATUS,
    GET_SYSTEM_INFO,
    GET_CPU_STATS,
    GET_MEMORY_STATS,
    LOGIN,
)
from .types import F5BigIPDevice, F5BigIPNode, F5BigIPStatus

HEADERS = {
    "Content-Type": "application/json"
}


class F5BigIPSession:
    def __init__(self, config: F5BigIPNode):
        self.config = config
        if self.config.api_token is None:
            if self.config.api_user is None or self.config.api_passwd is None:
                raise KeyError("either token or username/password needed")
        self.auth_token = None
        self.session = None
        self.base_url = self.config.url.rstrip('/')

    async def __aenter__(self):
        # Create aiohttp session
        connector_args = {}
        if self.config.verify_ssl is False:
            connector_args["ssl"] = False
        
        self.session = aiohttp.ClientSession(
            headers=HEADERS,
            connector=aiohttp.TCPConnector(**connector_args) if connector_args else None
        )
        
        # Authenticate
        if self.config.api_token is not None:
            self.auth_token = self.config.api_token.value
        else:
            await self._login()
        
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session is not None:
            await self.session.close()

    async def _login(self):
        """Login to F5 BIG-IP and get authentication token"""
        login_url = f"{self.base_url}/mgmt/shared/authn/login"
        payload = json.loads(LOGIN.format(
            user=self.config.api_user,
            passwd=self.config.api_passwd
        ))
        
        async with self.session.post(login_url, json=payload) as response:
            if response.status != 200:
                raise ValueError(f"Login failed with status {response.status}")
            data = await response.json()
            
            if os.getenv('ASSURANCE_API_DEBUG') is not None:
                print("# --- login ---------------------------------")
                print(json.dumps(data, indent=4))
            
            self.auth_token = data.get("token", {}).get("token")
            if not self.auth_token:
                raise ValueError("Failed to obtain authentication token")

    async def _get(self, endpoint: str) -> dict:
        """Make GET request to F5 REST API"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            **HEADERS,
            "X-F5-Auth-Token": self.auth_token
        }
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ValueError(f"API request failed: {endpoint} - Status: {response.status}")
            data = await response.json()
            
            if os.getenv('ASSURANCE_API_DEBUG') is not None:
                print(f"# --- GET {endpoint} ---------------------------------")
                print(json.dumps(data, indent=4))
            
            return data

    def _get_metafields(self, data: dict) -> dict:
        """Extract custom metadata fields (similar to FortiManager)"""
        addons = {}
        description = data.get("description", "")
        
        match self.config.owner:
            case "A1":
                # Parse description field for custom metadata
                if "A1-UUID:" in description or "A1_UUID:" in description:
                    for part in description.split():
                        if part.startswith("A1-UUID:") or part.startswith("A1_UUID:"):
                            addons['uuid'] = part.split(":", 1)[1].strip().lower()
                        if part.startswith("A1-MAINTENANCE:") or part.startswith("A1_MAINTENANCE:"):
                            addons['maintenance'] = part.split(":", 1)[1].strip()
        
        return addons

    async def get_devices(self) -> List[F5BigIPDevice]:
        """Get all devices in the BIG-IP cluster/standalone"""
        devices_data = await self._get(GET_DEVICES)
        
        # Get additional system info
        try:
            failover_data = await self._get(GET_FAILOVER_STATUS)
            cpu_data = await self._get(GET_CPU_STATS)
            memory_data = await self._get(GET_MEMORY_STATS)
        except Exception as e:
            if os.getenv('ASSURANCE_API_DEBUG') is not None:
                print(f"Warning: Could not fetch additional stats: {e}")
            failover_data = {}
            cpu_data = {}
            memory_data = {}
        
        devices: List[F5BigIPDevice] = []
        
        if "items" not in devices_data:
            return devices
        
        for device_info in devices_data["items"]:
            addons = self._get_metafields(device_info)
            
            # Extract failover state
            failover_state = "unknown"
            ha_status = "UNKNOWN"
            if "failoverState" in device_info:
                failover_state = device_info["failoverState"]
                ha_status = failover_state.upper()
            
            # Determine HA role
            ha_role = "standalone"
            if "haCapacity" in device_info:
                ha_capacity = device_info.get("haCapacity", 0)
                if ha_capacity > 0:
                    ha_role = "primary" if failover_state == "active" else "secondary"
            
            # Extract CPU and memory usage
            cpu_usage = 0
            memory_usage = 0
            
            # Parse stats if available
            if "entries" in cpu_data:
                try:
                    stats = list(cpu_data["entries"].values())[0]["nestedStats"]["entries"]
                    cpu_usage = int(stats.get("cpuInfoStat", {}).get("value", 0))
                except (KeyError, IndexError, ValueError):
                    pass
            
            if "entries" in memory_data:
                try:
                    stats = list(memory_data["entries"].values())[0]["nestedStats"]["entries"]
                    mem_used = stats.get("memoryUsed", {}).get("value", 0)
                    mem_total = stats.get("memoryTotal", {}).get("value", 1)
                    memory_usage = int((mem_used / mem_total) * 100) if mem_total > 0 else 0
                except (KeyError, IndexError, ValueError, ZeroDivisionError):
                    pass
            
            device = F5BigIPDevice(
                name=device_info.get("name", ""),
                hostname=device_info.get("hostname", device_info.get("name", "")),
                sn=device_info.get("chassisId", ""),
                management_ip=device_info.get("managementIp", ""),
                device_state=device_info.get("deviceState", "unknown"),
                failover_state=failover_state,
                ha_role=ha_role,
                ha_status=ha_status,
                platform=device_info.get("platformId", ""),
                version=device_info.get("version", ""),
                partition=device_info.get("partition", "Common"),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                **addons
            )
            devices.append(device)
        
        return devices

    async def get_status(self) -> F5BigIPStatus:
        """Get F5 BIG-IP system status"""
        system_info = await self._get(GET_SYSTEM_INFO)
        license_info = await self._get(GET_LICENSE)
        
        # Extract license status
        license_status = "unknown"
        if "entries" in license_info:
            try:
                license_entries = license_info["entries"]
                # F5 license format varies, try to get first entry
                first_key = list(license_entries.keys())[0]
                license_data = license_entries[first_key]["nestedStats"]["entries"]
                license_status = license_data.get("registrationKey", {}).get("description", "active")
            except (KeyError, IndexError):
                license_status = "active"
        
        # Extract system info
        if "entries" not in system_info:
            raise ValueError("Invalid system info response")
        
        sys_entries = list(system_info["entries"].values())[0]["nestedStats"]["entries"]
        
        return F5BigIPStatus(
            sn=sys_entries.get("bigipChassisSerialNum", {}).get("description", ""),
            hostname=sys_entries.get("hostName", {}).get("description", ""),
            version=sys_entries.get("version", {}).get("description", ""),
            platform=sys_entries.get("platform", {}).get("description", ""),
            license_status=license_status,
        )
