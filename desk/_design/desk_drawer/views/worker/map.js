function(doc) {
    if (doc.type == 'worker') {
        emit(doc.hostname, doc._rev);
    }
}