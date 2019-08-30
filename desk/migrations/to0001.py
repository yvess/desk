# coding: utf-8
  # python3


def main(doc, doc_type, db):
    def domainMigration(doc):
        # convert @ip_ -> $ip_ variables
        if 'a' in doc:
            for a in doc['a']:
                if a['ip'].startswith('@ip_'):
                    a['ip'] = a['ip'].replace('@ip_', '$ip_')
        # convert TXT txt -> content
        if 'txt' in doc:
            new_txt = []
            for txt in doc['txt']:
                if 'txt' in txt:
                    new_entry = {
                        'name': txt['name'],
                        'content': txt['txt']
                    }
                else:
                    new_entry = txt
                new_txt.append(new_entry)
            doc['txt'] = new_txt
        # type, sort key
        record_types = [
            ('a', 'host'),
            ('aaaa', 'host'),
            ('cname', 'alias'),
            ('mx', 'host'),
            ('txt', 'name'),
            ('srv', 'name'),
        ]
        # sort all list by key
        for rtype in record_types:
            if rtype[0] in doc:
                doc[rtype[0]] = sorted(
                    doc[rtype[0]], key=lambda item: item[rtype[1]]
                )
        # remove all frontend created attachments from doc
        if '_attachments' in doc:
            del doc['_attachments']
        # delete not needed properties
        if 'prev_rev' in doc:
            del doc['prev_rev']
        if 'prev_active_rev' in doc:
            del doc['prev_active_rev']
        if 'active_rev' in doc:
            del doc['active_rev']
        # set state to new
        doc['state'] = 'new'

    def mapMigration(doc):
        new_map = {}
        for map_key in doc['map']:
            new_map_key = map_key.replace('@ip_', '$ip_')
            new_map[new_map_key] = doc['map'][map_key]
        doc['map'] = new_map

    doc_types = {
        'domain': domainMigration,
        'map': mapMigration,
    }
    if (doc['type'] in doc_types):
        migrate = doc_types[doc['type']]
        migrate(doc)
    doc['version'] = 1
    db.save_doc(doc)
