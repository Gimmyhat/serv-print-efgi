from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserInfo(BaseModel):
    userType: Optional[str]
    oid: Optional[str]
    userName: Optional[str]
    fullName: Optional[str]

class OrganizationInfo(BaseModel):
    name: str
    agent: str
    address: str

class IndividualInfo(BaseModel):
    pass

class RegistryItem(BaseModel):
    id: str
    invNumber: Optional[str]
    name: Optional[str]
    informationDate: Optional[str]
    note: Optional[str]

class GeoInfoStorageOrganization(BaseModel):
    code: str
    value: str
    links: List[str] = []

class PurposeOfGeoInfoAccessDictionary(BaseModel):
    code: str
    value: str
    links: List[str] = []

class PrintRequest(BaseModel):
    operation: str
    id: str
    email: str
    phone: str
    applicantType: str
    organizationInfo: Optional[OrganizationInfo]
    individualInfo: Optional[IndividualInfo]
    purposeOfGeoInfoAccess: Optional[str]
    registryItems: List[RegistryItem]
    createdBy: UserInfo
    verifedBy: UserInfo
    creationDate: datetime
    type: str
    geoInfoStorageOrganization: GeoInfoStorageOrganization
    purposeOfGeoInfoAccessDictionary: PurposeOfGeoInfoAccessDictionary
    tfgiEmail: str 