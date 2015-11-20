function(doc) {
    if (doc.type == 'service') {
        if (doc.hasOwnProperty('addon_service_items')) {
            for each (addon in doc.addon_service_items) {
                emit([doc.service_type, doc.package_type, addon.itemType], {'_id': doc.client_id});
            }
        } else {
            emit([doc.service_type, doc.package_type, null], {'_id': doc.client_id});
        }
    }
}
