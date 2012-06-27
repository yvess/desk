from desk.pluginbase import DnsBase


class Powerdns(DnsBase):

    def update(self, input):
    	print self.doc
        return "done"