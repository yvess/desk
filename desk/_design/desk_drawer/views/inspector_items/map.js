function(doc) {
    if (doc.type == 'inspector') {
        for (var i = 0; i < doc.items.length; i++) {
            var item = doc.items[i];
            emit(item.domain, {
                'hostname': doc.hostname,
                'sub_type': doc.sub_type,
                'item_domain': item.domain,
                'item_type': item.type,
                'item_title': item.title,
                'item_path': item.path,
                'item_version':  item.version,
                'item_packages_versions':  item.packages_versions
            });
        }
    }
}
