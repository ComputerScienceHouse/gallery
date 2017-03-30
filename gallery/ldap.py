from functools import lru_cache

from gallery import ldap

@lru_cache(maxsize=1024)
def ldap_convert_uuid_to_displayname(uuid):
    if uuid == "root":
        return uuid
    return ldap.get_member(uuid).displayName

@lru_cache(maxsize=2014)
def ldap_is_eboard(uid):
    eboard_group = ldap.get_group('eboard')
    return eboard_group.check_member(ldap.get_member(uid, uid=True))

@lru_cache(maxsize=2014)
def ldap_is_rtp(uid):
    rtp_group = ldap.get_group('rtp')
    return rtp_group.check_member(ldap.get_member(uid, uid=True))
