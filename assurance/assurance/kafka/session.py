import json

import aiofiles
from kafka import KafkaProducer

from .types import KafkaNode


class KafkaSession:
    def __init__(self, config: KafkaNode):
        self.kafka_config = config
        self.producer = None

    async def __aenter__(self):
        ssl_params = {}
        if self.kafka_config.ssl_client_cert is not None:
            ssl_params = {
                'ssl_certfile': self.kafka_config.ssl_client_cert.certfile,
                'ssl_keyfile': self.kafka_config.ssl_client_cert.keyfile,
            }

        self.producer = KafkaProducer(bootstrap_servers=self.kafka_config.bootstrap_servers,
                                      value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                                      security_protocol=self.kafka_config.security_protocol,
                                      ssl_check_hostname=False,
                                      **ssl_params )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.producer is not None:
            self.producer.close()

    async def _read_password_from_file(self, filename) -> str:
        async with aiofiles.open(filename, 'r') as f:
            return await f.read()

    async def produce(self, topic: str, message: dict):
        if self.producer is not None:
            future = self.producer.send(topic, message)
            future.get(timeout=self.kafka_config.timeout)
