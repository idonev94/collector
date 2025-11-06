from pydantic import BaseModel, ConfigDict


class Customer(BaseModel):
    model_config = ConfigDict(extra='allow')
    sla_code: str
    kums: int
    lkms_id: int
    opennet_account: int
    mgmt_center_name: str
    nms_proactive: bool = False
