function(doc) {
    if ((doc.type == 'client') && (doc.is_billable == 1)) {
        emit(doc._id, doc._rev);
    }
}
