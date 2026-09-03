function(doc) {
    if (doc.type == 'service') {
        if (doc.hasOwnProperty('addon_service_items')) {
            for (var i = 0; i < doc.addon_service_items.length; i++) {
                var addon = doc.addon_service_items[i];
                emit([doc.service_type, addon.itemType], {'_id': doc.client_id, 'included_service_items': doc.included_service_items});
            }
        } else {
            emit([doc.service_type, null], {'_id': doc.client_id, 'included_service_items': doc.included_service_items});
        }
    }
}
