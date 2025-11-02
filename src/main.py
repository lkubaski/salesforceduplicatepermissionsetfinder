import argparse
import json
import logging
import sys
from dataclasses import asdict

from connection import Connection
from data_classes import PermissionSet, SystemPermission, ObjectPermissions, FieldPermissions, SetupEntityAccess, \
    PermissionSetTabSetting
from duplicate_finder import DuplicateFinder

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s - %(funcName)s - %(message)s')
logging.getLogger("urllib3").setLevel(logging.WARNING)

def write_json(permsets: list[PermissionSet]) -> None:
    logging.debug(">> << write_json")
    with open("permsets.json", "w") as file:
        json.dump([asdict(p) for p in permsets], file, indent=2)

def read_json() -> list[PermissionSet]:
    logging.debug(">> << read_json")
    with open("permsets.json") as file:
        data = json.load(file)
    permsets: list[PermissionSet] = []
    for d in data:
        permsets.append(
            PermissionSet(
                id=d["id"],
                name=d["name"],
                label=d["label"],
                user_license=d.get("user_license"),
                permission_set_license=d.get("permission_set_license"),
                system_perms=[SystemPermission(**sp) for sp in d.get("system_perms", [])],
                object_perms=[ObjectPermissions(**op) for op in d.get("object_perms", [])],
                field_perms=[FieldPermissions(**fp) for fp in d.get("field_perms", [])],
                setup_entity_access=[SetupEntityAccess(**se) for se in d.get("setup_entity_access", [])],
                permission_set_tab_setting=[PermissionSetTabSetting(**ts) for ts in d.get("permission_set_tab_setting", [])],
            )
        )
    return permsets

def main():
    # This is displayed when using the --help flag
    parser = argparse.ArgumentParser(
        # This formatter displays the description and epilog as written (ie: new lines are preserved)
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Permset Duplicate Finder',
    )

    parser.add_argument('-u', '--username', help='Salesforce username', required=True)
    parser.add_argument('-p', '--password', help='Salesforce password', required=True)
    parser.add_argument('-t', '--security-token', help='Security token (optional)')
    parser.add_argument('-d', '--domain', default='login', help='Salesforce domain (login, test, or custom)',
                        required=True)
    parser.add_argument('-s', '--sandbox', action='store_true', help='Connect to sandbox', required=False)
    parser.add_argument('-l', '--load', action='store_true', help='Load previously saved permission sets', required=False)
    args = parser.parse_args()

    if args.load:
        permsets = read_json()
    else:
        connection = Connection(
            username=args.username,
            password=args.password,
            security_token=args.security_token,
            domain=args.domain,
            sandbox=args.sandbox
        )
        if not connection.connect():
            sys.exit(1)

        logging.info("Loading system permissions")
        all_perms = connection.get_all_system_perms()
        logging.info(f"Successfully loaded {len(all_perms)} system permissions")
        logging.info("Loading permission sets")
        permsets = connection.get_permsets()
        logging.info(f"Successfully loaded {len(permsets)} permission sets")
        for i in range(len(permsets)):
            next_permset = permsets[i]
            logging.info(f"Loading permissions for permission set no {i+1}/{len(permsets)}: {next_permset.label}")
            system_perms = connection.get_system_perms(permset_id=next_permset.id, all_perms=all_perms)
            next_permset.system_perms = system_perms
            object_perms = connection.get_object_perms(permset_id=next_permset.id)
            next_permset.object_perms = object_perms
            field_perms = connection.get_field_perms(permset_id=next_permset.id)
            next_permset.field_perms = field_perms
            setup_entity_access = connection.get_setup_entity_access(permset_id=next_permset.id)
            next_permset.setup_entity_access = setup_entity_access
            tab_setting = connection.get_tab_setting(permset_id=next_permset.id)
            next_permset.permission_set_tab_setting = tab_setting
        write_json(permsets)

    logging.info("Finding duplicates")
    finder = DuplicateFinder(permsets)
    duplicates = finder.jaccard()
    for duplicate in duplicates:
        logging.info("")
        logging.info(f"Duplicate found: '{duplicate.permset1.get_displayable_label()}' and '{duplicate.permset2.get_displayable_label()}' with similarity {duplicate.similarity:.2f}")
        logging.info(f"\tNo common permissions: {len(duplicate.common_perms())}")
        if duplicate.similarity < 1.0:
            only_in_1 = duplicate.permset1_unique_perms()
            only_in_2 = duplicate.permset2_unique_perms()
            if only_in_1:
                logging.info(f"\t'{duplicate.permset1.label}' unique permissions:")
                for perm in only_in_1:
                    logging.info(f"\t\t{perm}")
            if only_in_2:
                logging.info(f"\t'{duplicate.permset2.label}' unique permissions:")
                for perm in only_in_2:
                    logging.info(f"\t\t{perm}")


if __name__ == '__main__':
    main()
