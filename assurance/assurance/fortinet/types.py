from typing import List

from pydantic import BaseModel

from assurance.base.http import HTTP


class FortiManagerException(Exception):
    pass

class FortiManagerNode(HTTP):
    owner: str = "A1"

class FortiManager(BaseModel):
    name: str
    node: FortiManagerNode
    sla_code: str = "L08"
    einstein: bool = True

class FortiManagerStatus(BaseModel):
    sn: str
    hostname: str
    version: str
    bios: str
    license_status: str

class FortinetHaSlave(BaseModel):
    name: str
    status: int
    role: str|int # int as workarround

class FortinetDevice(BaseModel):
    ip: str
    name: str
    hostname: str
    sn: str
    uuid: str = ""
    conn_status: str # up or down
    ha_mode: str
    ha_slave: List[FortinetHaSlave]|None = None
    maintenance: str = "" # non-empty means in maintenance
    adom: str = ""
    platform_str: str
    version: int
    vm_cpu: int
    vm_cpu_limit: int
    vm_mem: int
    vm_mem_limit: int
