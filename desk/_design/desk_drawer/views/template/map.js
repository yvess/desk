function(doc) {
    if (doc.type == 'template') {
        emit(doc._id, doc._rev);
    }
}