function(doc) {
    if (doc.type == 'order') {
        emit(doc._id, doc._rev);
    }
}
