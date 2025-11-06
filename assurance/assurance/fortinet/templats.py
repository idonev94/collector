LOGIN = """
{{
    "id": 1,
    "method": "exec",
    "params": [{{
        "data": {{
            "user": "{user}",
            "passwd": "{passwd}"
        }},
        "url": "sys/login/user"
    }}]
}}
"""

LOGOUT = """
{{
    "id": {id},
    "method": "exec",
    "params": [{{
        "url": "/sys/logout"
    }}],
    "session": "{session}"
}}
"""

GET_DEVICES = """
{{
    "method": "get",
    "params": [
        {{
        "url": "/dvmdb/device",
        "meta fields": [
            "A1-UUID",
            "A1_UUID",
            "A1-MAINTENANCE",
            "A1_MAINTENANCE",
            "A1_MAINTENANCE_CUSTOMER"
        ]
        }}
    ],
    "verbose": 1,
    "id": {id},
    "session": "{session}"
}}
"""

GET_DEVICES_WITH_ADOM = """
{{
    "method": "get",
    "params": [
        {{
        "url": "/dvmdb/adom/",        
        "expand member": [
            {{
                "fields": [
                    "name"
                ],
                "url": "device"
            }}
        ],
        "fields": [
            "name"
        ]
        }}     
    ],
    "verbose": 1,
    "id": {id},
    "session": "{session}"
}}
"""

GET_STATUS = """
{{
    "id": {id},
    "method": "get",
    "params": [{{
        "url": "/sys/status"
    }}],
    "session": "{session}"
}}
"""
