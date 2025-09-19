from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
from typing import Any, Union


class ServiceUserProfile(BaseModel):
    id: str  # ServiceUserId... is just a string.
    handle: str
    name: str
    avatarType: str
    avatarForegroundType: str
    avatarForegroundColor: str
    avatarBackgroundType: str
    avatarBackgroundColor: str
    bannerType: str
    aboutMe: str
    favorites: List[str]


class ServerAuthenticateRequest(BaseModel):
    type: str
    address: str
    time: int
    userProfile: ServiceUserProfile


class Like(BaseModel):
    type: Literal["like", "unlike"]


class ServiceUserProfileWithType(ServiceUserProfile):
    type: Literal["game"]


class ExternalServiceUserProfileWithType(ServiceUserProfile):
    type: Literal["external"]
    id_key: str


class ChartVisibilityData(BaseModel):
    status: Literal["PUBLIC", "PRIVATE", "UNLISTED"]


class ChartUploadData(BaseModel):
    rating: int
    title: str
    author: str
    artists: str

    tags: Optional[List[str]] = []
    description: Optional[str] = None
    # optional, can be False
    includes_background: bool = False
    includes_preview: bool = False


class ChartEditData(BaseModel):
    author: Optional[str] = None
    rating: Optional[int] = None
    title: Optional[str] = None
    artists: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []

    # files
    includes_background: Optional[bool] = False
    includes_preview: Optional[bool] = False
    delete_background: Optional[bool] = False
    delete_preview: Optional[bool] = False
    includes_audio: Optional[bool] = False
    includes_jacket: Optional[bool] = False
    includes_chart: Optional[bool] = False


class SessionKeyData(BaseModel):
    id: str
    user_id: str
    type: Literal["game", "external"]

class OAuth(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int

class SessionData(BaseModel):
    session_key: str
    expires: int

class Account(BaseModel):
    sonolus_id: str
    sonolus_handle: int
    discord_id: Optional[int] = None
    patreon_id: Optional[str] = None
    chart_upload_cooldown: Optional[datetime] = None
    sonolus_sessions: Optional[dict[Literal["game", "external"], dict[int, SessionData]]] = None
    oauth_details: Optional[dict[str, OAuth]] = None
    subscription_details: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    mod: bool = False
    banned: bool = False

class Chart(BaseModel):
    id: str
    author: str
    rating: int = 1
    chart_author: str
    title: str
    artists: Optional[str] = None
    jacket_file_hash: str
    music_file_hash: str
    chart_file_hash: str
    background_v1_file_hash: str
    background_v3_file_hash: str
    tags: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None
    preview_file_hash: Optional[str] = None
    background_file_hash: Optional[str] = None

class ChartDBResponse(Chart):
    status: Literal['UNLISTED', 'PRIVATE', 'PUBLIC']
    like_count: int
    created_at: datetime
    updated_at: datetime
    author_full: str

class ChartList(ChartDBResponse):
    total_count: int

class ChartByID(ChartDBResponse):
    log_like_score: float

class Comment(BaseModel):
    id: str
    commenter: str
    content: str
    created_at: datetime
    deleted_at: Optional[datetime] = None
    chart_id: str

class ExternalLogin(SessionData):
    session_key: str
    expires_at: datetime
    id_key: str

class DBID(BaseModel):
    id: str