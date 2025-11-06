from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel

from assurance.base.main import Config
from assurance.customer import Customer
from assurance.fortinet import FortiManager, FortiManagerStatus, FortinetDevice


class FortiConfig(Config):
    managers: List[FortiManager]
    data_index: str
    uuid_required: bool = True
    with_adoms: bool = True

class FortiManagerService(BaseModel):
    timestamp: str = datetime.now(timezone.utc).isoformat()
    status: FortiManagerStatus
    device: FortinetDevice
    customer: Customer|None = None
