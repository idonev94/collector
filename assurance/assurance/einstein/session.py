from datetime import datetime

from assurance.base.assurance import Assurance
from assurance.elasticsearch import ElasticsearchSession
from assurance.kafka import KafkaSession

from .types import (
    Alert,
    AlertEvent,
    AlertSeverity,
    Einstein,
    EinsteinMessage,
    KeepAliveAlert,
)


class EinsteinSession(Assurance, KafkaSession):

    def __init__(self, config: Einstein, elasticsearch: ElasticsearchSession):
        Assurance.__init__(self, __name__)
        KafkaSession.__init__(self, config.kafka)
        self.config = config
        self.elasticsearch = elasticsearch

    async def send(self, message: EinsteinMessage, send_to_einstein: bool = True):
        should_send = send_to_einstein and self.config.kafka.enabled and message.event != "CHECK" and message.event != "MAINT"
        prefix = "+" if should_send else "-"
        for mapping in self.config.node_mapping:
            if message.node_name == mapping.from_node_name:
                message.node_name = mapping.to_node_name
                message.organisation_id = mapping.to_organisation_id
        if self.config.clear_all:
            message.event = AlertEvent('UP').value
        self.logger.info("%sEinstein: %s/%s [%s/%s] %s", prefix, message.event, AlertSeverity(message.severity).name,
                         message.node_name, message.alert_type, message.short_summary)
        if should_send:
            await self.produce(self.config.kafka.topic, message.model_dump())

    async def get_last_alert(self, node_name: str, alert_type: str) -> dict|None:
        return await self.elasticsearch.get_last_alert(node_name, alert_type)

    async def get_last_keep_alive(self, node_name: str, alert_type: str) -> dict|None:
        return await self.elasticsearch.get_last_keep_alive(node_name, alert_type)

    async def send_keep_alive(self, alert: KeepAliveAlert):
        message = EinsteinMessage(
                    alert_type = alert.alert_type,
                    event = AlertEvent.KEEP_ALIVE,
                    short_summary = "Keepalive Message",
                    summary = alert.summary,
                    severity = AlertSeverity.NOTICE.value,
                    node_name = alert.node_name,
                    alert_source = alert.alert_source,
                    agent = alert.agent,
                    keepalive_timeout = self.config.keepalive_timeout,
                    sla_code = alert.sla_code
                )
        last_alert_dict = await self.get_last_keep_alive(message.node_name, message.alert_type)
        if last_alert_dict is not None:
            last_alert = EinsteinMessage(**last_alert_dict)
            current_occurence_time = datetime.fromisoformat(last_alert.last_occurence)
            current_occurence_time = datetime.fromisoformat(message.last_occurence)
            time_difference = current_occurence_time - current_occurence_time
            if time_difference.total_seconds() < self.config.keepalive_timeout * 60:
                message.first_occurence = last_alert.first_occurence
        await self.send(message)
        await self.elasticsearch.write_to_monthly(self.elasticsearch.config.keep_alive_index, message.model_dump())

    async def send_alert(self, alert: Alert):
        customer = {}
        if alert.customer is not None:
            customer = {
                'sla_code': alert.customer.sla_code,
                'location': alert.customer.lkms_id,
                'customer_number': alert.customer.opennet_account,
                'organisation_id': alert.customer.kums,
                'organisation_name': alert.customer.mgmt_center_name
            }
        message = EinsteinMessage(
            alert_type = alert.alert_type,
            event = alert.event,
            short_summary = alert.short_summary,
            summary = alert.summary,
            severity = alert.severity.value,
            node_name = alert.node_name,
            node_ip = alert.node_ip,
            alert_source = alert.alert_source,
            agent = alert.agent,
            **customer
        )
        last_alert_dict = await self.get_last_alert(message.node_name, message.alert_type)
        if last_alert_dict is not None:
            last_alert = EinsteinMessage(**last_alert_dict)
            message.first_occurence = last_alert.first_occurence
            if message.event == "DOWN" and last_alert.event != "DOWN":
                #self.logger.info("device '%s' is going down, reset first_occurance to %s", message.node_name, message.last_occurence)
                message.first_occurence = message.last_occurence
        await self.send(message, alert.einstein)
        await self.elasticsearch.write_to_monthly(self.elasticsearch.config.alert_index, {**message.model_dump(), "addons": alert.addons})
