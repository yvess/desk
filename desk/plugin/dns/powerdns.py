"""PowerDNS backend, talking the authoritative server's built-in HTTP API.

The API works in RRsets -- every record of one name and type at once -- which is
what the zone rebuild this worker does per record type already amounted to. It
also owns the SOA serial (`soa_edit_api` is `DEFAULT` on every zone the API
creates, giving the same YYYYMMDDnn serial the old code built by hand), and it
invalidates PowerDNS's own caches, so changes are served immediately.
"""
import re
from collections import OrderedDict

import httpx

from desk.plugin.dns import DnsBase, from_fqdn

SOA_FORMAT = (
    "{primary} {hostmaster} {serial} {soa_refresh} {soa_retry} "
    "{soa_expire} {soa_default_ttl}"
)
# every record type this worker manages; anything else in the zone is left alone
MANAGED_TYPES = ('SOA', 'NS', 'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV')
# a single <character-string> in a TXT record holds at most this many bytes
TXT_CHUNK = 255


def fqdn(name):
    """PowerDNS names records absolutely, with the trailing root dot."""
    return name if name.endswith('.') else f'{name}.'


def soa_mailbox(address):
    """The SOA hostmaster is a domain name, not an address: a@b -> a.b.

    The documents spell it `hostmaster@example.ch`, and writing that straight
    into the database (as the sqlite backend did) left PowerDNS serving an
    escaped `hostmaster\\@example.ch.`; the API rejects it outright.
    """
    local, at, domain = address.partition('@')
    return fqdn(f'{local}.{domain}') if at else fqdn(address)


def txt_content(value):
    """The document's TXT value as master-file content: quoted, escaped, and
    split into 255-byte strings, which is as much as one string may hold --
    a DKIM key is longer than that.
    """
    chunks = [
        value[i:i + TXT_CHUNK] for i in range(0, len(value), TXT_CHUNK)
    ] or ['']
    return ' '.join(
        '"{}"'.format(chunk.replace('\\', '\\\\').replace('"', '\\"'))
        for chunk in chunks
    )


def txt_value(content):
    """The reverse of txt_content: join the strings, drop the escapes."""
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', content)
    return ''.join(re.sub(r'\\(.)', r'\1', string) for string in strings)


class Powerdns(DnsBase):
    def __init__(self, settings, transport=None):
        self.doc = None
        self.domain = None
        self.api = httpx.Client(
            base_url=(
                f"{settings.powerdns_api_url.rstrip('/')}"
                "/api/v1/servers/localhost"
            ),
            headers={'X-API-Key': settings.powerdns_api_key},
            transport=transport,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.api.close()

    def _request(self, method, url, **kwargs):
        """Every call raises on an error status -- nothing is swallowed."""
        response = self.api.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def set_domain(self, domain):
        self.domain = domain

    @property
    def zone(self):
        return fqdn(self.domain)

    # -- turning a domain document into RRsets ---------------------------------

    def _record_content(self, name, item, rtype):
        """One record's content string, in the master-file syntax pdns wants."""
        key_id, value_id = rtype['key_id'], rtype['value_id']
        value = self._value_trans(value_id, rtype=rtype, item=item)
        if name == 'mx':
            return "{} {}".format(int(value['priority']), fqdn(value['host']))
        if name == 'srv':
            return "{priority} {weight} {port} {targethost}".format(
                **{**value, 'targethost': fqdn(value['targethost'])}
            )
        if name == 'txt':
            return txt_content(value)
        if name == 'cname':
            return fqdn(value)
        if value.startswith('$ip_'):
            return self.lookup_map[value]
        return value

    def _value_trans(self, value_id, rtype=None, item=None):
        if ',' in value_id:
            return {v: item[v] for v in value_id.split(',')}
        if 'value_trans' in rtype:
            return rtype['value_trans'](item[value_id], self.domain)
        return item[value_id]

    def _key_trans(self, key, rtype=None):
        if 'key_trans' in rtype:
            return rtype['key_trans'](key, self.domain)
        return key

    def _record_rrsets(self, only_rtype=None):
        """RRsets for the record types in `structure`, grouped by name+type."""
        grouped = OrderedDict()
        ttl = self.get_ttl(self.doc)
        for rtype in self.structure:
            name = rtype['name']
            if name not in self.doc or (only_rtype and name != only_rtype):
                continue
            for item in self.doc[name]:
                # MX records all hang off the zone apex, whatever their host
                if name == 'mx':
                    key = self.domain
                else:
                    key = self._key_trans(item[rtype['key_id']], rtype=rtype)
                entry = (fqdn(key), name.upper())
                grouped.setdefault(entry, []).append(
                    self._record_content(name, item, rtype)
                )
        return [
            self._rrset(name, rtype, contents, ttl)
            for (name, rtype), contents in grouped.items()
        ]

    def _rrset(self, name, rtype, contents, ttl):
        return {
            'name': name, 'type': rtype, 'ttl': ttl, 'changetype': 'REPLACE',
            'records': [
                {'content': content, 'disabled': False} for content in contents
            ],
        }

    def _apex_rrsets(self, serial):
        """The SOA and NS RRsets, rendered from the document.

        `serial` is what PowerDNS's DEFAULT soa-edit-api policy starts from:
        it bumps whatever it is handed, so an existing zone passes its current
        serial back in and keeps climbing instead of restarting.
        """
        ttl = self.get_ttl(self.doc)
        return [
            self._rrset(self.zone, 'SOA', [SOA_FORMAT.format(
                primary=fqdn(self.doc['soa_primary']),
                hostmaster=soa_mailbox(self.doc['soa_hostmaster']),
                serial=serial,
                **self.doc
            )], ttl),
            self._rrset(
                self.zone, 'NS',
                [fqdn(ns) for ns in self.doc['nameservers']], ttl
            ),
        ]

    def _current_serial(self, zone):
        for rrset in zone['rrsets']:
            if rrset['type'] == 'SOA' and rrset['records']:
                return rrset['records'][0]['content'].split()[2]
        return 1

    # -- zones -----------------------------------------------------------------

    def add_domain(self, domain=None):
        if domain:
            self.set_domain(domain)
        self._request('POST', '/zones', json={
            'name': self.zone, 'kind': 'Native', 'nameservers': [],
            'rrsets': self._apex_rrsets(serial=1) + self._record_rrsets(),
        })

    def del_domain(self, domain=None):
        if domain:
            self.set_domain(domain)
        self._request('DELETE', f'/zones/{self.zone}')

    def del_domains(self):
        for domain in self.get_domains():
            self.del_domain(domain)

    def get_domains(self):
        zones = self._request('GET', '/zones').json()
        return [zone['name'].rstrip('.') for zone in zones]

    # -- the three operations the worker drives --------------------------------

    def create(self):
        """Make the zone exist and match the document.

        CouchDB is authoritative, so an existing zone is patched into shape
        rather than refused: a task retried after a partial failure has to be
        able to succeed, and the zone keeps its SOA serial that way.
        """
        if not self.doc:
            return False
        self.set_domain(self.doc['domain'])
        if self.domain not in self.get_domains():
            self.add_domain()
            return True
        zone = self._request('GET', f'/zones/{self.zone}').json()
        desired = (
            self._apex_rrsets(self._current_serial(zone))
            + self._record_rrsets()
        )
        self._patch(zone, desired, MANAGED_TYPES)
        return True

    def update(self):
        """Rebuild the record types the diff touched, plus SOA and NS.

        The old backend deleted every row of a changed type and re-inserted
        it, then rewrote the SOA from the document; an RRset REPLACE is the
        same thing done atomically. SOA and NS go along every time because
        the diff only covers the record types in `structure` -- a changed
        refresh, hostmaster, nameserver or TTL would never show up in it.
        """
        if not self.doc or not self.diff:
            return False
        self.set_domain(self.doc['domain'])
        changed = {
            name for section in self.diff.values() for name in section
        }
        zone = self._request('GET', f'/zones/{self.zone}').json()
        desired = self._apex_rrsets(self._current_serial(zone))
        for name in changed:
            desired.extend(self._record_rrsets(only_rtype=name))
        types = ('SOA', 'NS') + tuple(name.upper() for name in changed)
        self._patch(zone, desired, types)
        return True

    def _patch(self, zone, desired, types):
        """One PATCH: REPLACE what the document has, DELETE what it dropped.

        A REPLACE only reaches the names it names, so every RRset of the
        `types` in the zone that `desired` does not cover is deleted
        explicitly; other types are left alone.
        """
        keep = {(rrset['name'], rrset['type']) for rrset in desired}
        gone = [
            {'name': rrset['name'], 'type': rrset['type'],
             'changetype': 'DELETE'}
            for rrset in zone['rrsets']
            if rrset['type'] in types
            and (rrset['name'], rrset['type']) not in keep
        ]
        self._request(
            'PATCH', f'/zones/{self.zone}', json={'rrsets': desired + gone}
        )

    def delete(self):
        if not self.doc:
            return False
        self.del_domain(self.doc['domain'])
        return True

    # -- reading a zone back ---------------------------------------------------

    def get_records(self, domain):
        """The zone as `dns-export-powerdns` wants it: rtype -> [(key, value)].

        Keys and values come back relative to the zone, the way they were
        written into the domain document.
        """
        self.set_domain(domain)
        zone = self._request('GET', f'/zones/{self.zone}').json()
        records = OrderedDict(
            (rtype, []) for rtype in
            ('a', 'aaaa', 'cname', 'mx', 'ns', 'txt', 'srv')
        )
        for rrset in zone['rrsets']:
            rtype = rrset['type'].lower()
            if rtype not in records:
                continue
            key = from_fqdn(rrset['name'].rstrip('.'), domain)
            for record in rrset['records']:
                records[rtype].append(
                    (key, self._export_value(rtype, record['content'], domain))
                )
        for rtype in records:
            records[rtype].sort()
        return records

    def _export_value(self, rtype, content, domain):
        if rtype == 'mx':  # "10 mx1.example.ch." -- priority is not exported
            content = content.split(' ', 1)[1]
        elif rtype == 'srv':  # priority is not exported, the rest is
            content = content.split(' ', 1)[1]
        elif rtype == 'txt':
            content = txt_value(content)
        if rtype in ('cname', 'mx', 'ns', 'txt', 'srv'):
            return from_fqdn(content.rstrip('.'), domain)
        return content
