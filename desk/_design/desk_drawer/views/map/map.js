function(doc) {
    if (doc.type == 'map') {
        emit(doc._id, doc._rev);
    }
}
