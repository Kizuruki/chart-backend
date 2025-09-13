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


class ServiceUserProfileWithType(ServiceUserProfile):
    type: Literal["game", "external"]


class ChartUploadData(BaseModel):
    sonolus_id: str
    chart_id: str
    rating: int
    title: str
    artists: str

    tags: Optional[List[str]]
    description: Optional[str]
    # optional, can be False
    includes_background: bool
    includes_preview: bool


class ChartEditData(BaseModel):
    sonolus_id: str
    chart_id: str

    rating: Optional[int]
    title: Optional[str]
    artists: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]

    # files
    includes_background: Optional[bool]
    includes_preview: Optional[bool]
    delete_background: Optional[bool]
    delete_preview: Optional[bool]
    includes_audio: Optional[bool]
    includes_jacket: Optional[bool]
    includes_chart: Optional[bool]
