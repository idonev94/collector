
from asyncio import TaskGroup
from typing import List, Tuple

from assurance.base.collector import Collector
from assurance.customer import CustomerClient
from assurance.einstein import (
    Alert,
    AlertEvent,
    AlertKey,
    AlertSeverity,
    KeepAliveAlert,
)
from assurance.fortinet import (
    FortiManager,
    FortiManagerSession,
    FortiManagerStatus,
    FortinetDevice,
)

from .types import FortiConfig, FortiManagerService


class FortiManagerCollector(Collector):
    def __init__(self, manager: FortiManager, config: FortiConfig):
        super().__init__(config, __name__)
        self.manager = manager

    @staticmethod
    def register(tg: TaskGroup, config: FortiConfig):
        for manager in config.managers:
            tg.create_task(FortiManagerCollector(manager, config).run())

    async def collect(self) -> Tuple[FortiManagerStatus, List[FortinetDevice]]:
        async with FortiManagerSession(self.manager.node) as fortimanager:
            status = await fortimanager.get_status()
            devices = await fortimanager.get_devices(self.config.with_adoms)
        return status, devices

    async def process(self, data: Tuple[FortiManagerStatus, List[FortinetDevice]]): # type: ignore
        status, devices = data
        await self.einstein.send_keep_alive(KeepAliveAlert( node_name = self.manager.name,
                                                            alert_type = "fortimanager_keepalive",
                                                            summary =   "Keepalive Message -> wenn ROT, Kontaktaufnahme mit Service Assurance Stack Rufbereitschaft (check producer collector-fortinet)",
                                                            agent = __class__.__name__,
                                                            alert_source = "Producer_COLLECTOR-FORTINET",
                                                            sla_code = self.manager.sla_code ))
        for device in devices:
            customer = await CustomerClient(self.elasticsearch).get_customer_info(uuid=device.uuid, hostname=self._node_name(device), uuid_required=self.config.uuid_required)
            service = FortiManagerService(device=device, customer=customer, status=status)
            await self.elasticsearch.write_to_monthly(self.config.data_index, service.model_dump())
            async for alert in self.check_alerts(service):
                if alert is not None:
                    alert.summary = f"Fortinet Firewall/Device '{alert.node_name}' is '{alert.event.value}'"
                    await self.einstein.send_alert(alert)

    def _node_name(self, device: FortinetDevice) -> str:
        if device.ha_mode != "standalone" and device.ha_slave is not None and len(device.ha_slave):
            for slave in device.ha_slave:
                if slave.role in ("master", 1):
                    return slave.name
        return device.name

    # --- alert handling ----------------------------------------------------------

    def _common_alert_params(self, service: FortiManagerService, alert_type: str) -> dict:
        einstein = False
        if self.manager.einstein and service.customer is not None:
            einstein = service.customer.nms_proactive
        alert_key = AlertKey(node_name = self._node_name(service.device),
                             alert_type=alert_type).model_dump()
        return {  **alert_key,
                    'agent': __class__.__name__,
                    'customer': service.customer,
                    'node_ip': service.device.ip,
                    'alert_source': f"Fortinet {service.status.hostname}",
                    'einstein': einstein,
                    'addons': { 'adom': service.device.adom }
        }

    def _check_device_status(self, service: FortiManagerService) -> Alert|None:
        common = self._common_alert_params(service, "fortimanager_device_status")
        # check maintenance flag first
        if service.device.maintenance != "":
            return Alert(**common, event=AlertEvent.MAINT, severity=AlertSeverity.NOTICE, short_summary="in maintenance")
        # service.customer is None
        if service.customer is None:
            return Alert(**common, event=AlertEvent.CHECK, severity=AlertSeverity.NOTICE,
                         short_summary=f"customer not found (uuid='{service.device.uuid}')")
        # service.customer is not None
        if service.device.conn_status == "up":
            return Alert(**common, event=AlertEvent.UP, severity=AlertSeverity.NOTICE, short_summary="device is online")
        return Alert(**common, event=AlertEvent.DOWN, severity=AlertSeverity.EMERGENCY, short_summary="Device unreachable")

    def _check_cluster_status(self, service: FortiManagerService) -> Alert|None:
        common = self._common_alert_params(service, "fortimanager_cluster_status")
        common["node_name"] = service.device.name # restore cluster-name
        match service.device.ha_mode:
            case "standalone":
                pass
            case "AP":
                if service.device.maintenance != "":
                    return Alert(**common, event=AlertEvent.MAINT, severity=AlertSeverity.NOTICE, short_summary="in maintenance")
                if service.device.ha_slave is None:
                    return Alert(**common, event=AlertEvent.CHECK, severity=AlertSeverity.NOTICE,
                            short_summary="ha_mode == 'AP' but no slaves")
                slaves = []
                for slave in service.device.ha_slave:
                    slaves.append(slave.name)
                common["summary"] = f"slaves: {', '.join(slaves)}"
                for slave in service.device.ha_slave:
                    if slave.status != 1:
                        return Alert(**common, event=AlertEvent.DOWN, severity=AlertSeverity.NOTICE,
                            short_summary=f"cluster redundancy lost, slave '{slave.name}' is down")
                if service.customer is None:
                    return Alert(**common, event=AlertEvent.CHECK, severity=AlertSeverity.NOTICE,
                           short_summary=f"customer not found (uuid='{service.device.uuid}')")
                return Alert(**common, event=AlertEvent.UP, severity=AlertSeverity.NOTICE,
                            short_summary="cluster is up")
            case _:
                self.runtime_error(f"ha_mode '{service.device.ha_mode}' not implemented")

    async def check_alerts(self, service: FortiManagerService):
        yield self._check_device_status(service)
        yield self._check_cluster_status(service)
