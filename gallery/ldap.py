from typing import Dict, List
import ldap as pyldap  # type: ignore
from typing import Optional, List, Dict
from csh_ldap import CSHLDAP, CSHMember


def is_member_of_group(member: CSHMember, group: str) -> bool:
    group_list = member.get("memberOf")
    for group_dn in group_list:
        if group == group_dn.split(",")[0][3:]:
            return True
    return False


class LDAPWrapper(object):
    def __init__(self, ldap: Optional[CSHLDAP], eboard: Optional[List[str]] = None, rtp: Optional[List[str]] = None):
        self._ldap = ldap
        self._eboard: List[str] = []
        self._rtp: List[str] = []

        if eboard:
            self._eboard = eboard
        if rtp:
            self._rtp = rtp

    def convert_uuid_to_displayname(self, uuid: str) -> str:
        if uuid == "root":
            return uuid
        if self._ldap is None:
            return "unknown"
        return self._ldap.get_member(uuid).displayName

    def is_eboard(self, uid: str) -> bool:
        if self._ldap is None:
            return uid in self._eboard
        return is_member_of_group(self._ldap.get_member(uid, uid=True), 'eboard')

    def is_rtp(self, uid: str) -> bool:
        if self._ldap is None:
            return uid in self._rtp
        rtp_group = self._ldap.get_group('rtp')
        return rtp_group.check_member(self._ldap.get_member(uid, uid=True))

    def get_members(self) -> List[Dict[str, str]]:
        if self._ldap is None:
            return []
        con = self._ldap.get_con()

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
