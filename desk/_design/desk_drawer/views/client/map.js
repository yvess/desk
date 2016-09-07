function(doc) {
    if (doc.type == 'client' && doc.state.indexOf('delete') < 0) {
        emit(doc.name, doc._rev);
    }
}
