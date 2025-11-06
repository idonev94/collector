from abc import ABC, abstractmethod
from asyncio import TaskGroup
from typing import Tuple

from pydantic import ValidationError

from assurance.base.assurance import Assurance, AssuranceException
from assurance.einstein import EinsteinSession
from assurance.elasticsearch import ElasticsearchSession


class Collector[T](ABC, Assurance):

    def __init__(self, config: T, name: str = __name__):
        Assurance.__init__(self, name)
        self.config: T = config
        self.elasticsearch: ElasticsearchSession
        self.einstein: EinsteinSession

    @staticmethod
    @abstractmethod
    def register(tg: TaskGroup, config: T):
        pass

    @abstractmethod
    async def collect(self) -> Tuple:
        pass

    @abstractmethod
    async def process(self, data: Tuple):
        pass

    async def run(self):
        try:
            data = await self.collect()
            async with ElasticsearchSession(self.config.elasticsearch.node) as self.elasticsearch: # type: ignore
                async with EinsteinSession(self.config.einstein, self.elasticsearch) as self.einstein: # type: ignore
                    await self.process(data)
        except ValidationError as e:
            error = self.pydantic_error(e)
            self.runtime_error(str(error))
            raise AssuranceException(error) from e

    def runtime_error(self, message: str):
        self.logger.error("Runtime Error: %s", message)
