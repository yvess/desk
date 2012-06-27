#from couchdbkit import Server, Consumer
#s = Server()
#db = s['desk_drawer']
#c = Consumer(db)
#def print_line(line):
#    print "got %s" % line
#c.wait(print_line,since=0) # Go into receive loop


import sys
import os
from couchdbkit import Server
from couchdbkit.changes import ChangesStream
#import desk.plugin
sys.path.append('/mnt/hgfs')


s = Server(uri="http://qs:5984")
desk_drawer = s['desk_drawer']

#settings = desk_drawer.get("worker-settings")

hostname = os.uname()[1]
provides = {}

# setup worker
for worker in desk_drawer.list("desk_drawer/list_docs", "worker", include_docs=True, startkey=hostname, endkey=hostname):
    provides = worker['provides']
print provides

with ChangesStream(desk_drawer, feed="continuous", heartbeat=True, filter="desk_drawer/queue") as queue:
    for job in queue:
        print job
        for item in desk_drawer.view('desk_drawer/todo'):
            doc = item['value']
            if doc['type'] in provides:
                for service_settings in provides[doc['type']]:
                    if 'server_type' in service_settings and 'master' in service_settings['server_type'] or not 'server_type' in service_settings:
                        print doc['type'], service_settings['backend']
                        ServiceClass = None
                        print  doc['type'], service_settings['backend']
                        import desk.plugin
                        print getattr(desk.plugin, 'dns')
                        #print "desk.plugin", desk.plugin
                        #getattr(desk.plugin, doc['type'])
                        #try:
                        #    ServiceClass = getattr(getattr(desk.plugin, doc['type']), service_settings['backend'])
                        #except AttributeError:
                        #    print "not found"
                        #if ServiceClass:
                        #    service = ServiceClass(doc)
                        #    service.update()
