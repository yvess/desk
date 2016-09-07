function(doc) {
    if (doc.type == 'domain' && doc.state.indexOf('delete') < 0) {
        emit(doc._id, doc._rev);
    }
}
