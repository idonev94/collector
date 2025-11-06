"""
F5 BIG-IP REST API Templates
These templates are used with the F5 iControl REST API
"""

# Authentication endpoint - F5 uses token-based auth
LOGIN = """
{{
    "username": "{user}",
    "password": "{passwd}",
    "loginProviderName": "tmos"
}}
"""

# Get system information
GET_STATUS = "/mgmt/tm/sys/global-settings"

# Get software version
GET_VERSION = "/mgmt/tm/sys/software/volume"

# Get devices in device group (for HA clusters)
GET_DEVICES = "/mgmt/tm/cm/device"

# Get device details with stats
GET_DEVICE_STATS = "/mgmt/tm/cm/device/stats"

# Get failover status
GET_FAILOVER_STATUS = "/mgmt/tm/cm/failover-status"

# Get device groups (HA configuration)
GET_DEVICE_GROUPS = "/mgmt/tm/cm/device-group"

# Get license information
GET_LICENSE = "/mgmt/tm/sys/license"

# Get system info
GET_SYSTEM_INFO = "/mgmt/tm/sys/system-info"

# Get hardware information
GET_HARDWARE = "/mgmt/tm/sys/hardware"

# Get CPU stats
GET_CPU_STATS = "/mgmt/tm/sys/host-info/stats"

# Get memory stats
GET_MEMORY_STATS = "/mgmt/tm/sys/memory/stats"

# Get disk usage
GET_DISK_STATS = "/mgmt/tm/sys/disk/logical-disk/stats"

# Get all virtual servers
GET_VIRTUAL_SERVERS = "/mgmt/tm/ltm/virtual"

# Get all pools
GET_POOLS = "/mgmt/tm/ltm/pool"

# Get pool members with stats
GET_POOL_MEMBERS = "/mgmt/tm/ltm/pool/{pool_name}/members"

# Get pool stats
GET_POOL_STATS = "/mgmt/tm/ltm/pool/{pool_name}/stats"
