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
from assurance.f5 import (
    F5BigIP,
    F5BigIPSession,
    F5BigIPStatus,
    F5BigIPDevice,
)

from .types import F5Config, F5BigIPService


class F5BigIPCollector(Collector):
    def __init__(self, bigip: F5BigIP, config: F5Config):
        super().__init__(config, __name__)
        self.bigip = bigip

    @staticmethod
    def register(tg: TaskGroup, config: F5Config):
        for bigip in config.devices:
            tg.create_task(F5BigIPCollector(bigip, config).run())

    async def collect(self) -> Tuple[F5BigIPStatus, List[F5BigIPDevice]]:
        async with F5BigIPSession(self.bigip.node) as f5session:
            status = await f5session.get_status()
            devices = await f5session.get_devices()
        return status, devices

    async def process(self, data: Tuple[F5BigIPStatus, List[F5BigIPDevice]]):  # type: ignore
        status, devices = data
        
        # Send keepalive for the F5 BIG-IP system
        await self.einstein.send_keep_alive(
            KeepAliveAlert(
                node_name=self.bigip.name,
                alert_type="f5_bigip_keepalive",
                summary="Keepalive Message -> wenn ROT, Kontaktaufnahme mit Service Assurance Stack Rufbereitschaft (check producer collector-f5)",
                agent=__class__.__name__,
                alert_source="Producer_COLLECTOR-F5",
                sla_code=self.bigip.sla_code
            )
        )
        
        # Process each device in the cluster
        for device in devices:
            customer = await CustomerClient(self.elasticsearch).get_customer_info(
                uuid=device.uuid,
                hostname=self._node_name(device),
                uuid_required=self.config.uuid_required
            )
            
            service = F5BigIPService(device=device, customer=customer, status=status)
            
            # Write device data to Elasticsearch
            await self.elasticsearch.write_to_monthly(
                self.config.data_index,
                service.model_dump()
            )
            
            # Generate and send alerts
            async for alert in self.check_alerts(service):
                if alert is not None:
                    alert.summary = f"F5 BIG-IP Device '{alert.node_name}' is '{alert.event.value}'"
                    await self.einstein.send_alert(alert)

    def _node_name(self, device: F5BigIPDevice) -> str:
        """Get the appropriate node name for the device"""
        # For HA pairs, use the active device name
        if device.ha_role != "standalone" and device.failover_state == "active":
            return device.name
        # For standby or standalone, use hostname or name
        return device.hostname if device.hostname else device.name

    # --- alert handling ----------------------------------------------------------

    def _common_alert_params(self, service: F5BigIPService, alert_type: str) -> dict:
        """Build common alert parameters"""
        einstein = False
        if self.bigip.einstein and service.customer is not None:
            einstein = service.customer.nms_proactive
        
        alert_key = AlertKey(
            node_name=self._node_name(service.device),
            alert_type=alert_type
        ).model_dump()
        
        return {
            **alert_key,
            'agent': __class__.__name__,
            'customer': service.customer,
            'node_ip': service.device.management_ip,
            'alert_source': f"F5 BIG-IP {service.status.hostname}",
            'einstein': einstein,
            'addons': {
                'partition': service.device.partition,
                'platform': service.device.platform,
                'ha_role': service.device.ha_role
            }
        }

    def _check_device_status(self, service: F5BigIPService) -> Alert | None:
        """Check device connectivity and operational status"""
        common = self._common_alert_params(service, "f5_bigip_device_status")
        
        # Check maintenance flag first
        if service.device.maintenance != "":
            return Alert(
                **common,
                event=AlertEvent.MAINT,
                severity=AlertSeverity.NOTICE,
                short_summary="in maintenance"
            )
        
        # Check if customer info is missing
        if service.customer is None:
            return Alert(
                **common,
                event=AlertEvent.CHECK,
                severity=AlertSeverity.NOTICE,
                short_summary=f"customer not found (uuid='{service.device.uuid}')"
            )
        
        # Check device state
        if service.device.device_state == "offline":
            return Alert(
                **common,
                event=AlertEvent.DOWN,
                severity=AlertSeverity.EMERGENCY,
                short_summary="Device offline/unreachable"
            )
        
        if service.device.device_state in ("active", "standby"):
            return Alert(
                **common,
                event=AlertEvent.UP,
                severity=AlertSeverity.NOTICE,
                short_summary=f"device is {service.device.device_state}"
            )
        
        # Unknown state
        return Alert(
            **common,
            event=AlertEvent.CHECK,
            severity=AlertSeverity.WARNING,
            short_summary=f"device state is '{service.device.device_state}'"
        )

    def _check_ha_status(self, service: F5BigIPService) -> Alert | None:
        """Check High Availability cluster status"""
        common = self._common_alert_params(service, "f5_bigip_ha_status")
        
        # Only check HA for non-standalone devices
        if service.device.ha_role == "standalone":
            return None
        
        # Check maintenance
        if service.device.maintenance != "":
            return Alert(
                **common,
                event=AlertEvent.MAINT,
                severity=AlertSeverity.NOTICE,
                short_summary="in maintenance"
            )
        
        # Check failover state
        if service.device.failover_state == "offline":
            return Alert(
                **common,
                event=AlertEvent.DOWN,
                severity=AlertSeverity.CRITICAL,
                short_summary="HA member is offline - redundancy lost"
            )
        
        if service.device.failover_state in ("active", "standby"):
            common["summary"] = f"HA Role: {service.device.ha_role}, State: {service.device.failover_state}"
            
            if service.customer is None:
                return Alert(
                    **common,
                    event=AlertEvent.CHECK,
                    severity=AlertSeverity.NOTICE,
                    short_summary=f"customer not found (uuid='{service.device.uuid}')"
                )
            
            return Alert(
                **common,
                event=AlertEvent.UP,
                severity=AlertSeverity.NOTICE,
                short_summary=f"HA pair operational - {service.device.failover_state}"
            )
        
        # Unknown failover state
        return Alert(
            **common,
            event=AlertEvent.CHECK,
            severity=AlertSeverity.WARNING,
            short_summary=f"Unknown HA state: {service.device.failover_state}"
        )

    def _check_resource_usage(self, service: F5BigIPService) -> Alert | None:
        """Check CPU and memory usage"""
        common = self._common_alert_params(service, "f5_bigip_resource_usage")
        
        # Skip if customer not found or in maintenance
        if service.customer is None or service.device.maintenance != "":
            return None
        
        # Check CPU usage
        if service.device.cpu_usage > 90:
            return Alert(
                **common,
                event=AlertEvent.DOWN,
                severity=AlertSeverity.WARNING,
                short_summary=f"High CPU usage: {service.device.cpu_usage}%",
                addons={
                    **common['addons'],
                    'cpu_usage': service.device.cpu_usage,
                    'memory_usage': service.device.memory_usage
                }
            )
        
        # Check memory usage
        if service.device.memory_usage > 90:
            return Alert(
                **common,
                event=AlertEvent.DOWN,
                severity=AlertSeverity.WARNING,
                short_summary=f"High memory usage: {service.device.memory_usage}%",
                addons={
                    **common['addons'],
                    'cpu_usage': service.device.cpu_usage,
                    'memory_usage': service.device.memory_usage
                }
            )
        
        # Resources are OK
        if service.device.cpu_usage > 0 or service.device.memory_usage > 0:
            return Alert(
                **common,
                event=AlertEvent.UP,
                severity=AlertSeverity.NOTICE,
                short_summary=f"Resources OK (CPU: {service.device.cpu_usage}%, MEM: {service.device.memory_usage}%)"
            )
        
        return None

    async def check_alerts(self, service: F5BigIPService):
        """Generate all alerts for the device"""
        yield self._check_device_status(service)
        yield self._check_ha_status(service)
        yield self._check_resource_usage(service)
