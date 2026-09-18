import abc
from socket import gethostbyname
import dns.resolver


class DnsValidator(object):
    """Ask the nameservers whether a zone really says what the document says.

    Used by `dworker dns-check`: the worker writes zones through the PowerDNS
    API, this reads them back over DNS, which is the only check that covers the
    whole path.
    """

    map_doc_id = 'map-ips'

    def __init__(self, doc, lookup=None, resolver=None, lookup_map=None):
        self.doc = doc
        self.domain = doc['domain']
        self.resolver = resolver or dns.resolver.Resolver()
        # nameserver name -> address, for names the host cannot resolve itself
        self.lookup = lookup or {}
        # the `$ip_` map, so those values can be compared
        self.lookup_map = lookup_map or {}
        self.valid = []

    def _setup_resolver(self, ns):
        # a nameserver without an override is looked up the normal way
        self.resolver.nameservers = [
            self.lookup.get(ns) or gethostbyname(ns)
        ]

    def _answers(self, name, record_type, answer_attr):
        """The values the nameserver returns, as strings.

        A record that is not there is not an error here -- it is an answer of
        nothing, which is what makes the comparison below report it invalid.
        A nameserver that does not have the zone at all answers REFUSED, which
        dnspython raises as NoNameservers; that is the same answer of nothing.
        """
        try:
            response = self.resolver.resolve(name, record_type)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers):
            return []
        answers = []
        for answer in response:
            if record_type == 'TXT':
                # TXT rdata carries the strings a record was split into
                answers.append(
                    ''.join(part.decode() for part in answer.strings)
                )
            else:
                answers.append(str(getattr(answer, answer_attr)))
        return answers

    def _expected(self, item, item_key, record_type, is_fqdn):
        value = str(item[item_key])
        if value.startswith('$ip_'):
            value = self.lookup_map[value]
        if is_fqdn and not value.endswith("."):
            # an MX host is already qualified; the rest name this zone
            zone = None if record_type == "MX" else self.domain
            value = f"{to_fqdn(value, zone)}."
        return value

    def _query_name(self, item, q_key):
        if q_key == 'domain':
            return self.domain
        if q_key in ('host', 'alias', 'name'):
            return to_fqdn(item[q_key], self.domain)
        return item[q_key]

    def _validate(self, record_type, item_key, q_key='domain',
                  answer_attr='address'):
        for item in self.doc.get(record_type.lower(), []):
            answers = self._answers(
                self._query_name(item, q_key), record_type, answer_attr
            )
            is_fqdn = any(answer.endswith(".") for answer in answers)
            self.valid.append(
                self._expected(item, item_key, record_type, is_fqdn)
                in answers
            )

    def _checked(self):
        is_valid = all(self.valid)
        self.valid = []
        return is_valid

    def do_check(self):
        for ns in self.doc['nameservers']:
            self._setup_resolver(ns)
            self._validate('A', 'ip', q_key='host')
            self._validate('AAAA', 'ipv6', q_key='host')
            self._validate('MX', 'host', answer_attr='exchange')
            self._validate('MX', 'priority', answer_attr='preference')
            self._validate(
                'CNAME', 'host', q_key='alias', answer_attr='target'
            )
            # the content of each TXT record, asked for at its own name
            self._validate('TXT', 'content', q_key='name')
        return self._checked()


def to_fqdn(name, domain=None):
    """Qualify a record name inside its zone.

    A trailing dot means the name is already absolute -- the stored form drops
    it. `@` is the zone apex. Anything else gets the domain appended, if there
    is one to append.
    """
    if name.endswith('.'):
        return name[:-1]
    if name == '@':
        return domain or name
    if domain:
        return f'{name}.{domain}'
    return name


def from_fqdn(name, domain):
    """The inverse of to_fqdn: a name in `domain` as the document spells it."""
    name, matched_domain, remainder = name.partition(f'.{domain}')
    if name == domain:
        return "@"
    if not matched_domain and not name.endswith('.'):
        name = f'{name}.'
    if name == ".":
        return ""
    return name


def get_providers(doc):
    provider_key = 'nameservers'
    nameservers = [to_fqdn(provider) for provider in doc[provider_key]]
    return nameservers


class DnsBase(object, metaclass=abc.ABCMeta):
    # filled by set_lookup_map(); empty until then so a $ip_ lookup fails
    # with a KeyError naming the value instead of an AttributeError
    lookup_map = {}
    # set_diff() is only called for a 'changed' document that has an active
    # revision to compare against; update() has to cope with the other case
    diff = None
    structure = [
        {
            'name': 'a',
            'key_id': 'host',
            'key_trans': to_fqdn,
            'value_id': 'ip',
        },
        {
            'name': 'aaaa',
            'key_id': 'host',
            'key_trans': to_fqdn,
            'value_id': 'ipv6',
        },
        {
            'name': 'cname',
            'key_id': 'alias',
            'key_trans': to_fqdn,
            'value_id': 'host',
            'value_trans': to_fqdn
        },
        {
            'name': 'mx',
            'key_id': 'host',
            'value_id': 'host,priority'
        },
        {
            'name': 'txt',
            'key_id': 'name',
            'key_trans': to_fqdn,
            'value_id': 'content',
        },
        {
            'name': 'srv',
            'key_id': 'name',
            # no key_trans: don't add domains automatically
            'value_id': 'priority,weight,port,targethost'
        }
    ]
    map_doc_id = 'map-ips'

    @abc.abstractmethod
    def set_domain(self, domain):
        """Set the current domain."""

    @abc.abstractmethod
    def create(self):
        """Create the dns record."""

    @abc.abstractmethod
    def update(self, record):
        """Update the dns record."""

    @abc.abstractmethod
    def delete(self, record):
        """delete the dns record."""

    @abc.abstractmethod
    def add_domain(self, domain):
        """add new domain"""

    @abc.abstractmethod
    def del_domain(self, domain):
        """del domain"""

    @abc.abstractmethod
    def get_domains(self):
        """get all domain names"""

    @abc.abstractmethod
    def get_records(self, domain=None):
        """get all records"""

    def set_docs(self, doc, active_doc=None):
        """sets the doc to use"""
        self.doc = doc
        self.active_doc = active_doc

    def set_diff(self, diff):
        """sets the json diff to use"""
        self.diff = diff

    def set_lookup_map(self, doc):
        self.lookup_map = doc['map']

    def get_ttl(self, doc):
        if 'ttl' in doc:
            return doc['ttl']
        if 'soa_default_ttl' in doc:
            return doc['soa_default_ttl']
        return 86400
