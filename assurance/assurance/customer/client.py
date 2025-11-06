
from assurance.elasticsearch import ElasticsearchSession

from .types import Customer


class CustomerClient:
    def __init__(self, elasticsearch: ElasticsearchSession):
        self.elasticsearch = elasticsearch

    async def get_customer_info(self, uuid: str|None = None, hostname: str|None = None,
                                uuid_required: bool = False) -> Customer|None:
        search_host = None if uuid_required else hostname
        customer = await self.elasticsearch.search_nms_managed_account(uuid=uuid, hostname=search_host)
        if customer is not None:
            return Customer(**customer)
        return None
