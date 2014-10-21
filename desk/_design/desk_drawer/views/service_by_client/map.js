function(doc) {
    if (doc.type == 'service') {
        emit(doc.client_id, doc._id);
    }
}
