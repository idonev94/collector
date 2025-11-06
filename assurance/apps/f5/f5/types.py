from typing import List
from pydantic import BaseModel
from assurance.base.http import HTTP


class F5BigIPException(Exception):
    pass


class F5BigIPNode(HTTP):
    owner: str = "A1"


class F5BigIP(BaseModel):
    name: str
    node: F5BigIPNode
    sla_code: str = "L08"
    einstein: bool = True


class F5BigIPStatus(BaseModel):
    sn: str
    hostname: str
    version: str
    platform: str
    license_status: str


class F5PoolMember(BaseModel):
    name: str
    address: str
    state: str
    session: str
    availability_state: str


class F5BigIPDevice(BaseModel):
    name: str
    hostname: str
    sn: str
    uuid: str = ""
    management_ip: str
    device_state: str  # active, standby, offline
    failover_state: str  # active, standby, offline
    ha_role: str  # primary, secondary, standalone
    ha_status: str  # ACTIVE, STANDBY, OFFLINE
    platform: str
    version: str
    maintenance: str = ""  # non-empty means in maintenance
    partition: str = "Common"
    # Resource utilization
    cpu_usage: int = 0
    memory_usage: int = 0
    disk_usage: int = 0
