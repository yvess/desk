function(doc) {
    if (doc.type == 'domain') {
        emit(doc.client_id, doc._id);
    }
}
