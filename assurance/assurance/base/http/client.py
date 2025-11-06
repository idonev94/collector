import aiohttp

from .types import HTTP

JSON_HEADERS = {
    "Content-Type": "application/json"
}

class HttpClient:
    def __init__(self, config: HTTP):
        self.config = config
        self.client_args = {}
        if config.proxy is not None:
            self.client_args["proxy"] = config.proxy
        self.request_args = {}
        if config.verify_ssl is False:
            self.request_args["ssl"] = False
        self.params = {}
        if self.config.api_token is not None:
            self.params[self.config.api_token.name] = self.config.api_token.value

    async def json_post(self, data: dict) -> dict:
        async with aiohttp.ClientSession(**self.client_args) as session:
            async with session.post(self.config.url,
                                    json=data,
                                    headers=JSON_HEADERS,
                                    params=self.params,
                                    **self.request_args) as response:
                return await response.json()
