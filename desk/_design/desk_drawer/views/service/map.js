function(doc) {
    if (doc.type == 'service') {
        emit(doc._id, doc._rev);
    }
}
