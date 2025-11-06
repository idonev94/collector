from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    name: str
    value: str

class HTTP(BaseModel):
    model_config = ConfigDict(strict=True)
    url: str
    api_user: str|None = None
    api_passwd: str|None = None
    api_token: Token|None = None
    verify_ssl: bool = True
    proxy: str|None = None
