function(doc) {
    if (doc.client_id) {
        emit(doc.client_id, doc._id);
    }
}
