import logging

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed, SalesforceError
from typing import Any, get_args

from data_classes import PermissionSet, ObjectPermissions, FieldPermissions, SetupEntityAccess, OBJECT_PERMISSIONS, \
    FIELD_PERMISSIONS, PermissionSetTabSetting, SystemPermission


class Connection:
    """Handles Salesforce connection and basic operations."""

    def __init__(self,
                 username: str,
                 password: str,
                 security_token: str | None = None,
                 domain: str = 'login',
                 sandbox: bool = False):
        """
        Initialize Salesforce connector.

        Args:
            username: Salesforce username
            password: Salesforce password
            security_token: Security token (optional, will prompt if needed)
            domain: Salesforce domain (login, test, or custom)
            sandbox: Whether to connect to sandbox
        """
        self.username = username
        self.password = password
        self.security_token = security_token
        self.domain = domain
        self.sandbox = sandbox
        self.sf:Salesforce = None  # type: ignore

    def connect(self) -> bool:
        """
        Establish connection to Salesforce.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logging.info(f"Connecting to Salesforce as {self.username}...")

            # Build connection parameters
            connection_params:dict[str, Any] = {
                'username': self.username,
                'password': self.password,
                'domain': self.domain
            }

            # Add security token if provided
            # https://help.salesforce.com/s/articleView?id=xcloud.user_security_token.htm&type=5
            # If the option is not visible, that may be because the org uses IP whitelisting
            # -> https://help.salesforce.com/s/articleView?id=000386179&type=1
            if self.security_token:
                connection_params['security_token'] = self.security_token

            # Add sandbox flag if needed
            if self.sandbox:
                connection_params['sandbox'] = True

            # Attempt connection
            self.sf = Salesforce(**connection_params)  # type: ignore

            # Test the connection by making a simple query
            test_query = self.sf.query("SELECT Id FROM User LIMIT 1")

            if test_query['records']:
                logging.info(f"✅ Successfully connected to Salesforce!")
                return True
            else:
                logging.info("❌ Connection failed: Could not retrieve user information")
                return False

        except SalesforceAuthenticationFailed as e:
            logging.info(f"❌ Authentication failed: {str(e)}")
            logging.info("💡 Tip: You might need a security token. Get it from:")
            logging.info("   Setup → My Personal Information → Reset My Security Token")
            return False
        except SalesforceError as e:
            logging.info(f"❌ Salesforce error: {str(e)}")
            return False
        except Exception as e:
            logging.info(f"❌ Unexpected error: {str(e)}")
            return False

    def get_all_system_perms(self) -> list[SystemPermission]:
        logging.debug(f">> get_all_system_perms")
        result:list[SystemPermission] = list()
        # https://simple-salesforce.readthedocs.io/en/latest/user_guide/misc.html
        ps = self.sf.PermissionSet.describe()  # type: ignore
        for field in ps['fields']:
            if field['name'].startswith("Permissions"):
                result.append(SystemPermission(name=field['name']))
        logging.debug(f"<< get_all_system_perms: returning nb perms={len(result)}")
        return result

    def get_permsets(self) -> list[PermissionSet]:
        logging.debug(f">> get_permsets")
        result: list[PermissionSet] = list()
        # https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_permissionset.htm
        query = """
                SELECT Id, Name, Label, LicenseId
                FROM PermissionSet
                WHERE IsOwnedByProfile = false
                ORDER BY Name
                """
        response = self.sf.query_all(query)
        for ps in response['records']:
            license_id = ps.get('LicenseId')
            psl:str | None = None
            ul:str | None = None
            if license_id:
                psl_query = f"SELECT Id, MasterLabel FROM PermissionSetLicense WHERE Id ='{license_id}'"
                psl_result = self.sf.query_all(psl_query)
                if psl_result['records']:
                    psl_result = psl_result['records'][0]
                    psl = psl_result['MasterLabel']
                else:
                    ul_query = f"SELECT Id, Name FROM UserLicense WHERE Id ='{license_id}'"
                    ul_result = self.sf.query_all(ul_query)
                    if ul_result['records']:
                        ul_result = ul_result['records'][0]
                        ul = ul_result['Name']

            permset = PermissionSet(id=ps['Id'],
                                    name=ps['Name'],
                                    label=ps['Label'],
                                    user_license=ul,
                                    permission_set_license=psl
                                    )
            result.append(permset)
        logging.debug(f"<< get_permsets: returning nb permsets={len(result)}")
        return result

    def get_system_perms(self, permset_id: str, all_perms: list[SystemPermission]) -> list[SystemPermission]:
        logging.debug(f">> get_system_perms: permset_id={permset_id}")
        result:list[SystemPermission] = list()
        all_perm_names = [p.name for p in all_perms]
        query = f"""
                SELECT Id, Name, {",".join(all_perm_names)}
                FROM PermissionSet 
                WHERE Id = '{permset_id}' 
                """
        response = self.sf.query_all(query)
        response = response['records'][0]
        for next_perm in all_perms:
            if next_perm.name in response and response[next_perm.name] is True:
                result.append(next_perm)
        logging.debug(f"<< get_system_perms: returning nb records={len(result)}")
        return result

    def get_object_perms(self, permset_id: str) -> list[ObjectPermissions]:
        logging.debug(f">> get_object_perms: permset_id={permset_id}")
        result: list[ObjectPermissions] = list()
        all_perms = list(get_args(OBJECT_PERMISSIONS))
        #all_perms = ['PermissionsCreate', 'PermissionsRead', 'PermissionsEdit', 'PermissionsDelete', 'PermissionsViewAllRecords', 'PermissionsModifyAllRecords']
        # Note: some objects like 'Badge' don't have object permissions (access is given via user permissions)
        query = f"""
                SELECT SObjectType, {','.join(all_perms)}
                FROM ObjectPermissions 
                WHERE ParentId = '{permset_id}' 
                """
        response = self.sf.query_all(query)
        for next_record in response['records']:
            next_object_perms = [key for key, value in next_record.items() if (value and key in all_perms)]
            op = ObjectPermissions(
                sobject_type=next_record['SobjectType'],
                perms=next_object_perms)
            result.append(op)
        logging.debug(f"<< get_object_perms: returning nb records={len(result)}")
        return result

    def get_field_perms(self, permset_id: str) -> list[FieldPermissions]:
        logging.debug(f">> get_field_perms: permset_id={permset_id}")
        result: list[FieldPermissions] = list()
        all_perms = list(get_args(FIELD_PERMISSIONS))
        #all_perms = ['PermissionsRead', 'PermissionsEdit']
        # Important: this query actually does not return all FLS, only the custom ones
        # For example, there is some OOTB FLS on the Account object that are not returned here
        query = f"""
                SELECT SobjectType, Field, {','.join(all_perms)}
                FROM FieldPermissions 
                WHERE ParentId = '{permset_id}'
                """
        response = self.sf.query_all(query)
        for next_record in response['records']:
            next_object_perms = [key for key, value in next_record.items() if (value and key in all_perms)]
            fp = FieldPermissions(sobject_type=next_record['SobjectType'],
                                  sobject_field=next_record['Field'],
                                  perms=next_object_perms)
            result.append(fp)
        logging.debug(f"<< get_field_perms: returning nb records={len(result)}")
        return result

    def get_setup_entity_access(self, permset_id: str) -> list:
        logging.debug(f">> get_setup_entity_access: permset_id={permset_id}")
        result: list[SetupEntityAccess] = list()
        query = f"""
                SELECT SetupEntityId, SetupEntityType
                FROM SetupEntityAccess 
                WHERE ParentId = '{permset_id}'
                """
        response = self.sf.query_all(query)
        for next_record in response['records']:
            sea = SetupEntityAccess(setup_entity_type=next_record['SetupEntityType'], setup_entity_id=next_record['SetupEntityId'])
            result.append(sea)
        logging.debug(f"<< get_setup_entity_access: returning nb records={len(result)}")
        return result

    def get_tab_setting(self, permset_id: str) -> list:
        logging.debug(f">> get_tab_setting: permset_id={permset_id}")
        result: list[PermissionSetTabSetting] = list()
        query = f"""
                SELECT Name, Visibility
                FROM PermissionSetTabSetting 
                WHERE ParentId = '{permset_id}'
                """
        response = self.sf.query_all(query)
        for next_record in response['records']:
            psts = PermissionSetTabSetting(name=next_record['Name'], visibility=next_record['Visibility'])
            result.append(psts)
        logging.debug(f"<< get_tab_setting: returning nb records={len(result)}")
        return result
