from typing import List

from pydantic import BaseModel, ConfigDict


class SSLClientCert(BaseModel):
    certfile: str
    keyfile: str


class KafkaNode(BaseModel):
    model_config = ConfigDict(strict=True)
    bootstrap_servers: List[str]
    timeout: int = 10
    topic: str
    security_protocol: str = "PLAINTEXT"
    ssl_client_cert: SSLClientCert|None = None
    enabled: bool = True
