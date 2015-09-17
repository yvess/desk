function(doc) {
    if (doc.type == 'service_definition') {
        emit(doc._id, doc._rev);
    }
}
