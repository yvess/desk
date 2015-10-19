function(doc) {
    if (doc.type == 'domain') {
        emit(doc.domain, doc._id);
    }
}
