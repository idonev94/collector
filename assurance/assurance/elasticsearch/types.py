

from pydantic import BaseModel, ConfigDict


class ElasticsearchNode(BaseModel):
    model_config = ConfigDict(strict=True)
    host: str
    user: str
    passwd: str
    use_ssl: bool = True
    verify_ssl: bool = True
    alert_index: str = "nms_einstein-alerts_"
    keep_alive_index: str = "nms_einstein-keep_alive_"

class Elasticsearch(BaseModel):
    model_config = ConfigDict(strict=True)
    node: ElasticsearchNode
