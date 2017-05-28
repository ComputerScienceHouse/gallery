from gallery import ldap

def ldap_convert_uuid_to_displayname(uuid):
    if uuid == "root":
        return uuid
    return ldap.get_member(uuid).displayName

def ldap_is_eboard(uid):
    eboard_group = ldap.get_group('eboard')
    return eboard_group.check_member(ldap.get_member(uid, uid=True))

def ldap_is_rtp(uid):
    rtp_group = ldap.get_group('rtp')
    return rtp_group.check_member(ldap.get_member(uid, uid=True))
