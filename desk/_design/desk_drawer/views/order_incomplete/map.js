function(doc) {
    if (doc.type == 'order' && doc.state != 'new' && doc.state != 'done') {
        emit(doc.date, [doc._id, doc._rev]);
    }
}
