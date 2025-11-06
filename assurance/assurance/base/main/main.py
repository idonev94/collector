import asyncio
import glob
import logging
import os
from abc import ABC, abstractmethod

import yaml
from dotenv import load_dotenv


class Main(ABC):

    def __init__(self):
        self._logging_config()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def handler(self):
        pass

    def run(self):
        asyncio.run(self.handler())

    def _logging_config(self):
        formatstr = "%(name)s %(levelname)s %(message)s"
        if os.getenv('ASSURANCE_DEBUG') is not None:
            logging.basicConfig(level=logging.DEBUG, format=formatstr)
            return
        logging.basicConfig(level=logging.INFO, format=formatstr)
        for v in logging.Logger.manager.loggerDict.values():
            if isinstance(v, logging.Logger):
                if not v.name.startswith('assurance'):
                    v.disabled = True

    def read_config(self) -> dict:
        load_dotenv()
        configdir = os.getenv('ASSURANCE_CONFIG_DIR')
        if configdir is None:
            raise ValueError("environment ASSURANCE_CONFIG_DIR not set")
        if not os.path.isdir(configdir):
            raise ValueError(f"ASSURANCE_CONFIG_DIR={configdir} is not a directory")
        filtered_envs = {k: v for k, v in os.environ.items() if k.startswith("ASSURANCE_")}
        config = {"config_dir": configdir}
        for file in glob.glob(f"{configdir}/*.yaml"):
            self.logger.debug("read config file %s", file)
            with open(file, "r", encoding="utf-8") as f:
                plain_config = f.read().format(**filtered_envs)
                config = {**config, **yaml.safe_load(plain_config)}
        return config
