function(doc) {
    if (doc.type == 'client') {
        if (doc.hasOwnProperty('state') && doc.state.indexOf('delete') >= 0) {
            // do nothing
        } else {
            emit(doc.name, doc._rev);
        }
    }
}
