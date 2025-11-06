#!/usr/bin/env python3.12

import asyncio

from fortinet import FortiConfig, FortiManagerCollector

from assurance.base.main import Main


class Fortinet(Main):
    async def handler(self):
        config = FortiConfig(**self.read_config())
        async with asyncio.TaskGroup() as tg:
            FortiManagerCollector.register(tg, config)

if __name__ == '__main__':
    Fortinet().run()
