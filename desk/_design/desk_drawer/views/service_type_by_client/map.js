function(doc) {
    if (doc.type == 'service') {
        emit([doc.service_type, doc.client_id], doc._id);
    }
}
