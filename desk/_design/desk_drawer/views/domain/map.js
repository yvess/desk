function(doc) {
    if (doc.type == 'domain') {
        emit(doc._id, doc._rev);
    }
}