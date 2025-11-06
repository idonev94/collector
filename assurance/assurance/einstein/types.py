from datetime import datetime, timezone
from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict

from assurance.customer import Customer
from assurance.kafka import KafkaNode


class AlertEvent(Enum):
    UP = "UP"
    DOWN = "DOWN"
    KEEP_ALIVE = "KEEP_ALIVE"
    CHECK = "CHECK"
    MAINT = "MAINT"

class AlertSeverity(Enum):
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5

class NodeMapping(BaseModel):
    from_node_name: str
    to_node_name: str
    to_organisation_id: int


class Einstein(BaseModel):
    keepalive_timeout: int
    kafka: KafkaNode
    node_mapping: List[NodeMapping] = []
    clear_all: bool = False


class EinsteinKey(BaseModel):
    alert_type: str
    first_occurence: str = datetime.now(timezone.utc).isoformat()

# see: https://tasktrack.telekom.at/confluence/display/SA/Test+support+documentation
# key = (alert_type, organisation_id, first_occurence)
class EinsteinMessage(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    event: AlertEvent
    alert_type: str
    summary: str
    short_summary: str
    sla_code: str = ""
    severity: int
    node_name: str
    node_ip: str = ''
    organisation_id: int = 0
    organisation_name: str = 'A1 Telekom Austria AG'
    alert_source: str
    agent: str
    first_occurence: str = datetime.now(timezone.utc).isoformat()
    last_occurence: str = datetime.now(timezone.utc).isoformat()
    location: str|int = 0
    customer_number: int = 0
    keepalive_timeout: int = 20    

class AlertKey(BaseModel):
    node_name: str
    alert_type: str

class AlertWithAgent(AlertKey):
    agent: str
    alert_source: str
    sla_code: str = ""

class Alert(AlertWithAgent):
    event: AlertEvent
    severity: AlertSeverity
    short_summary: str
    summary: str = ""
    node_ip: str = "0.0.0.0"
    customer: Customer|None = None
    einstein: bool = True
    addons: dict = {}

class KeepAliveAlert(AlertWithAgent):
    summary: str
