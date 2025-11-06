import warnings
from datetime import datetime, timezone

from elasticsearch7 import AsyncElasticsearch

from .types import ElasticsearchNode

warnings.filterwarnings("ignore", message=".*built-in security features are not enabled")
warnings.filterwarnings("ignore", message=".*using SSL with verify_certs=False is insecure.")

class ElasticsearchSession:
    def __init__(self, config: ElasticsearchNode):
        self.config = config
        self.client: AsyncElasticsearch

    async def __aenter__(self):
        proto = 'https://' if self.config.use_ssl else 'http://'
        host = f"{proto}{self.config.host}"
        self.client = AsyncElasticsearch(
            hosts=[host],
            http_auth=(self.config.user, self.config.passwd),
            verify_certs=self.config.verify_ssl
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.close()

    async def write(self, index: str, data: dict) -> None:
        if "@timestamp" not in data:
            data["@timestamp"] = data.pop("timestamp") if "timestamp" in data else datetime.now(timezone.utc).isoformat()
        await self.client.index(index=index, document=data) # pylint: disable=unexpected-keyword-arg,no-value-for-parameter

    async def search_last(self, index: str, matches: dict) -> dict|None:
        terms = []
        for key, value in matches.items():
            terms.append({
                "term": {
                    key: value
                }
            })
        body = {
            "query": {
                "bool": {
                    "must": terms
                }
            },
            "sort": { "@timestamp" : "desc" },
            "size": 1
        }
        response = await self.client.search(index=index, body=body)        
        if response["hits"]["total"]["value"] == 0:
            return None
        return response["hits"]["hits"][0]["_source"]

    async def write_to_monthly(self, index_prefix: str, data: dict):
        slot = datetime.now().strftime("%Y.%m")
        await self.write(f"{index_prefix}{slot}", data)

    async def search_nms_managed_account(self, uuid: str|None = None, hostname: str|None = None) -> dict|None:
        if uuid is not None:
            if (result := await self.search_last("nms_managed_accounts-raw_*", {"uuid.keyword": uuid})) is not None:
                return result
        if hostname is not None:
            if (result := await self.search_last("nms_managed_accounts-raw_*", {"nms_hostname": hostname})) is not None:
                return result
        return None

    async def _get_last_alert(self, index: str, node_name: str, alert_type: str) -> dict|None:
        data = await self.search_last(f"{index}*", {
                                            "node_name.keyword": node_name,
                                            "alert_type.keyword": alert_type
                                        })
        if data is None:
            return None
        return data

    async def get_last_alert(self, node_name: str, alert_type: str) -> dict|None:
        return await self._get_last_alert(self.config.alert_index, node_name, alert_type)

    async def get_last_keep_alive(self, node_name: str, alert_type: str) -> dict|None:
        return await self._get_last_alert(self.config.keep_alive_index, node_name, alert_type)
