function(doc) {
    if (doc.type == 'client' && doc.is_billable == 1 ) {
        if (doc.state && doc.state.indexOf('delete') > 0) {
            // do nothing
        } else {
            emit(doc._id, doc._rev);
        }
    }
}
