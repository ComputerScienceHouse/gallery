from gallery import ldap
import ldap as pyldap

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

def ldap_get_members():
    con = ldap.get_con()

    res = con.search_s(
            "dc=csh,dc=rit,dc=edu",
            pyldap.SCOPE_SUBTREE,
            "(memberof=cn=member,cn=groups,cn=accounts,dc=csh,dc=rit,dc=edu)",
            ["ipaUniqueID", "displayName"])

    members = filter(lambda m: 'displayName' in m[1], res)

    return [{
        "name": m[1]['displayName'][0].decode('utf-8'),
        "uuid": m[1]['ipaUniqueID'][0].decode('utf-8')
        } for m in members]

