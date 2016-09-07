function(doc) {
    if ((doc.type == 'client') && (doc.is_billable == 1) && doc.state.indexOf('delete') < 0) {
        emit(doc._id, doc._rev);
    }
}
