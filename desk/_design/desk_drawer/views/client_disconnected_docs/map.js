function(doc) {
    if (doc.type == 'client') {
        emit(doc._id, 1);
    } else if (doc.client_id) {
        emit(doc.client_id, 0);
    }
}
