#!/usr/bin/env python3.12
import asyncio

from f5 import F5Config, F5BigIPCollector
from assurance.base.main import Main


class F5BigIP(Main):
    async def handler(self):
        config = F5Config(**self.read_config())
        async with asyncio.TaskGroup() as tg:
            F5BigIPCollector.register(tg, config)


if __name__ == '__main__':
    F5BigIP().run()
