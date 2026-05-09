from pydantic import BaseModel

class TelegramSendCode(BaseModel):
    phone: str

class TelegramVerifyCode(BaseModel):
    phone: str
    code: str
    phone_code_hash: str

class TelegramTwoFA(BaseModel):
    phone: str
    phone_code_hash: str
    password: str

class DeepSyncRequest(BaseModel):
    chat_ids: list[str]
    limit: int = 500
    days: int = 90

class DiscoveryJoinRequest(BaseModel):
    chat_id: str
    username: str | None = None
    deep_sync_days: int = 365
