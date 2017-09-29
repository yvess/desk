function(doc) {
    if (doc.type == 'inspector') {
        emit(doc._id, doc._rev);
    }
}
