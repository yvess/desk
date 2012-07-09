from desk.pluginbase.dns import DnsBase

class Powerdns(DnsBase):
    def __init__(self, doc):
        print "doc:", doc
        self.doc = doc
    def update(self):
        print self.doc, "PD update"
        return "done"
