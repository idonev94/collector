from pydantic import BaseModel, ConfigDict

from assurance.einstein import Einstein
from assurance.elasticsearch import Elasticsearch
from assurance.mapper import Mapping


class Config(BaseModel):
    model_config = ConfigDict(strict=True)
    config_dir: str
    elasticsearch: Elasticsearch
    einstein: Einstein
    mapping: Mapping|None = None
