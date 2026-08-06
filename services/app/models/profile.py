from pydantic import BaseModel, Field

# ProfileUpdate
class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None

# ProfilePublic
class ProfilePublic(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    phone: str | None = None
    address: str | None = None