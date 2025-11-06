import json
import os
from typing import List

from assurance.base.http import HttpClient

from .templats import GET_DEVICES, GET_DEVICES_WITH_ADOM, GET_STATUS, LOGIN, LOGOUT
from .types import FortiManagerNode, FortiManagerStatus, FortinetDevice

HEADERS = {
    "Content-Type": "application/json"
}

class FortiManagerSession():
    def __init__(self, config: FortiManagerNode):
        self.config = config
        if self.config.api_token is None:
            if self.config.api_user is None or self.config.api_passwd is None:
                raise KeyError("either token or username/password needed")
        self.id = 0
        self.session = None
        self.http_client = HttpClient(self.config)

    async def __aenter__(self):
        self.session = ""
        if self.config.api_token is None:
            login = await self._login()
            self.session = login["session"]
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.config.api_token is None:
            await self._logout()

    def _format(self, template: str, **kwargs) -> dict:
        self.id += 1
        return json.loads(template.format(id=self.id, session=self.session, **kwargs))

    def _check_result(self, response: dict):
        if response["result"][0]["status"]["code"] != 0:
            raise ValueError(f'invalid response from server: {response["result"][0]["status"]["message"]}')

    async def _login(self):
        payload = self._format(LOGIN, user=self.config.api_user, passwd=self.config.api_passwd)
        response = await self.http_client.json_post(payload)
        if os.getenv('ASSURANCE_API_DEBUG') is not None:
            print("# --- login ---------------------------------")
            print(json.dumps(response, indent=4))
        self._check_result(response)
        return response

    async def _logout(self):
        payload = self._format(LOGOUT)
        response = await self.http_client.json_post(payload)
        if os.getenv('ASSURANCE_API_DEBUG') is not None:
            print("# --- logout ---------------------------------")
            print(json.dumps(payload, indent=4))
            print(json.dumps(response, indent=4))
        self._check_result(response)
        return response

    # get aonaccount
    def _get_metafields(self, data: dict) -> dict:
        key = "meta fields"
        addons = {}
        match self.config.owner:
            case "A1":
                if key in data:
                    if "A1-UUID" in data[key]:
                        addons['uuid'] = data[key]["A1-UUID"].strip().lower()
                    if "A1_UUID" in data[key]:
                        addons['uuid'] = data[key]["A1_UUID"].strip().lower()
                    if "A1-MAINTENANCE" in data[key]:
                        addons['maintenance'] = data[key]["A1-MAINTENANCE"]
                    if "A1_MAINTENANCE" in data[key]:
                        addons['maintenance'] = data[key]["A1_MAINTENANCE"]
                    if "A1_MAINTENANCE_CUSTOMER" in data[key]:
                        addons['maintenance'] = data[key]["A1_MAINTENANCE_CUSTOMER"]
        return addons

    # get uuid and remove meta fields
    def _normalize(self, data: dict, fields: List[str]) -> dict:
        out = dict(data)
        addons = self._get_metafields(data)
        for key in data:
            if key not in fields:
                del out[key]
        return {**out, **addons}

    async def get_devices(self, with_adoms: bool) -> List[FortinetDevice]:     
        fields = FortinetDevice.model_json_schema()["properties"].keys()
        fieldnames = ", ".join([f"\"{x}\"" for x in fields])
        payload = self._format(GET_DEVICES, fields=fieldnames)
        response = await self.http_client.json_post(payload)
        if os.getenv('ASSURANCE_API_DEBUG') is not None:
            print("# --- get_devices ---------------------------------")
            print(json.dumps(payload, indent=4))
            print(json.dumps(response, indent=4))
        self._check_result(response)
        
        devices_adoms = {}
        if with_adoms:
            devices_adoms = await self.get_devices_adoms()

        devices: List[FortinetDevice] = []
        for data in response["result"][0]["data"]:
            adom = devices_adoms[data["name"]] if data["name"] in devices_adoms else ""
            devices.append(FortinetDevice(**self._normalize(data, fields), adom=adom))
        return devices
    
    async def get_devices_adoms(self) -> dict:
        payload = self._format(GET_DEVICES_WITH_ADOM)
        response = await self.http_client.json_post(payload)
        if os.getenv('ASSURANCE_API_DEBUG') is not None:
            print("# --- get_devices ---------------------------------")
            print(json.dumps(payload, indent=4))
            print(json.dumps(response, indent=4))
        self._check_result(response)
        devices = {}
        for adom in response["result"][0]["data"]:
            adom_name = adom["name"]
            if "expand member" in adom and "device" in adom["expand member"]:
                for device in adom["expand member"]["device"]:
                    devices[device["name"]] = adom_name
        return devices

    async def get_status(self) -> FortiManagerStatus:
        payload = self._format(GET_STATUS)
        response = await self.http_client.json_post(payload)
        if os.getenv('ASSURANCE_API_DEBUG') is not None:
            print("# --- get_status ---------------------------------")
            print(json.dumps(payload, indent=4))
            print(json.dumps(response, indent=4))
        self._check_result(response)
        data = response["result"][0]["data"]
        return FortiManagerStatus(
            sn=data["Serial Number"],
            hostname=data["Hostname"],
            version=f"{data['Major']}.{data['Minor']}.{data['Patch']}",
            bios=data["BIOS version"],
            license_status=data["License Status"],
        )
