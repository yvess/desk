function(doc) {
    if (doc.type == 'service') {
        emit([doc.service_type], {'_id': doc.client_id, 'included_service_items': doc.included_service_items});
    }
}
