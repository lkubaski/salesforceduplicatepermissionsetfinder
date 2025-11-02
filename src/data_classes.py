from dataclasses import dataclass, field
from typing import Literal, Union


@dataclass(frozen=True)
class SystemPermission:
    name: str

ENTITY_TYPES = Literal[
    "ApexClass", "ApexPage", "BotDefinition", "ConnectedApplication", "CustomEntityDefinition",
    "CustomPermission", "EmailRoutingAddress", "ExternalClientApplication", "ExternalCredentialParameter",
    "FlowDefinition", "MessagingChannel", "OrgWideEmailAddress", "ServiceProvider", "StandardInvocableActionType",
    "TabSet"
]

@dataclass(frozen=True)
class SetupEntityAccess:
    # https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_setupentityaccess.htm
    setup_entity_type: ENTITY_TYPES
    setup_entity_id: str

OBJECT_PERMISSIONS = Literal['PermissionsCreate', 'PermissionsRead', 'PermissionsEdit', 'PermissionsDelete',
     'PermissionsViewAllRecords', 'PermissionsModifyAllRecords']

@dataclass
class ObjectPermissions:
    """
    https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_objectpermissions.htm
    """
    sobject_type: str
    perms: list[str] = field(default_factory=list)

    def __eq__(self, other):
        if not isinstance(other, ObjectPermissions):
            return NotImplemented
        # Compare perms as tuple to ensure hashable, order matters
        return (self.sobject_type, tuple(self.perms)) == (other.sobject_type, tuple(other.perms))

    def __hash__(self):
        # Convert list to tuple for hashing
        return hash((self.sobject_type, tuple(self.perms)))

FIELD_PERMISSIONS = Literal['PermissionsRead', 'PermissionsEdit']

@dataclass
class FieldPermissions:
    """
    https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_fieldpermissions.htm
    """
    sobject_type: str
    sobject_field: str
    perms: list[FIELD_PERMISSIONS] = field(default_factory=list)

    def __eq__(self, other):
        if not isinstance(other, FieldPermissions):
            return NotImplemented
        # Compare perms as tuple for hashable comparison
        return (
            self.sobject_type,
            self.sobject_field,
            tuple(self.perms)
        ) == (
            other.sobject_type,
            other.sobject_field,
            tuple(other.perms)
        )

    def __hash__(self):
        # Convert list to tuple for hashing
        return hash((self.sobject_type, self.sobject_field, tuple(self.perms)))


TAB_VISIBILITY = Literal['DefaultOff', 'DefaultOn']

@dataclass(frozen=True)
class PermissionSetTabSetting:
    """
    https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_permissionsettabsetting.htm
    """
    name: str
    visibility: TAB_VISIBILITY

ALL_PERMS_TYPE = Union[
    SystemPermission,
    ObjectPermissions,
    FieldPermissions,
    SetupEntityAccess,
    PermissionSetTabSetting,
]

@dataclass
class PermissionSet:
    """
    https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_permissionset.htm
    """
    id: str
    name: str
    label: str
    user_license: str | None  = None
    permission_set_license: str | None = None

    system_perms: list[SystemPermission] = field(default_factory=list)
    object_perms: list[ObjectPermissions] = field(default_factory=list)
    field_perms: list[FieldPermissions] = field(default_factory=list)
    setup_entity_access: list[SetupEntityAccess] = field(default_factory=list)
    permission_set_tab_setting: list[PermissionSetTabSetting] = field(default_factory=list)

    def get_displayable_label(self):
        prefix = ""
        if self.user_license:
            prefix = f"(user_license={self.user_license})"
        elif self.permission_set_license:
            prefix = f"(permset_license={self.permission_set_license})"
        return f"{self.label} {prefix}"

    def get_all_perms(self) -> list[ALL_PERMS_TYPE]:
        all_perms:list[ALL_PERMS_TYPE] = []
        all_perms.extend(self.system_perms)
        all_perms.extend(self.object_perms)
        all_perms.extend(self.field_perms)
        all_perms.extend(self.setup_entity_access)
        all_perms.extend(self.permission_set_tab_setting)
        return all_perms

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PermissionSet):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class JaccardDifference:
    permset1: PermissionSet
    permset2: PermissionSet
    similarity: float

    def common_perms(self) -> list[ALL_PERMS_TYPE]:
        perms1 = set(self.permset1.get_all_perms())
        perms2 = set(self.permset2.get_all_perms())
        common_perms = perms1.intersection(perms2)
        return sorted(list(common_perms), key=lambda x: x.__class__.__name__)

    def permset1_unique_perms(self) -> list[ALL_PERMS_TYPE]:
        perms1 = set(self.permset1.get_all_perms())
        perms2 = set(self.permset2.get_all_perms())
        unique_perms1 = perms1 - perms2
        return sorted(list(unique_perms1), key=lambda x: x.__class__.__name__)

    def permset2_unique_perms(self) -> list[ALL_PERMS_TYPE]:
        perms1 = set(self.permset1.get_all_perms())
        perms2 = set(self.permset2.get_all_perms())
        unique_perms2 = perms2 - perms1
        return sorted(list(unique_perms2), key=lambda x: x.__class__.__name__)
