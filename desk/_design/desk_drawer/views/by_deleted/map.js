function(doc) {
    if (doc.hasOwnProperty('state')) {
        if (doc.state == 'delete' || doc.state == 'deleted')
            emit(doc._id, doc._rev);
    }
}
