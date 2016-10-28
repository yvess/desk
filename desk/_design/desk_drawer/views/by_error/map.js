function(doc) {
    if (doc.hasOwnProperty('state')) {
        if (doc.state == 'error')
            emit(doc._id, doc._rev);
    }
}
