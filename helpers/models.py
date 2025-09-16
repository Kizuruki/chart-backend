from pydantic import BaseModel
from typing import List, Literal, Optional


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
    chart_id: str
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
    chart_id: str

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
