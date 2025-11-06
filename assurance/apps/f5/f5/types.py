from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel

from assurance.base.main import Config
from assurance.customer import Customer
from assurance.f5 import F5BigIP, F5BigIPStatus, F5BigIPDevice


class F5Config(Config):
    devices: List[F5BigIP]
    data_index: str
    uuid_required: bool = True


class F5BigIPService(BaseModel):
    timestamp: str = datetime.now(timezone.utc).isoformat()
    status: F5BigIPStatus
    device: F5BigIPDevice
    customer: Customer | None = None
