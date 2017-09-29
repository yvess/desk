function(doc) {
    if (doc.type == 'client' && doc.state.indexOf('delete') < 0 && doc.is_billable == 1 ) {
        emit(doc._id, doc._rev);
    }
}
