function(doc) {
    if ((doc.type == 'client') && (doc.isBillable == 1)) {
        emit(doc._id, doc._rev);
    }
}
