from functools import lru_cache

from gallery import ldap

@lru_cache(maxsize=1024)
def ldap_convert_uuid_to_displayname(uuid):
    if uuid == "root":
        return uuid
    return ldap.get_member(uuid).displayName
