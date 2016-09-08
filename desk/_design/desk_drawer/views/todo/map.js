function(doc) {
    if ((doc.state && doc.state == 'changed')
        || (doc.state && doc.state == 'new')
        || (doc.state && doc.state == 'delete')) {
        if (doc.type != 'order') {
            emit(doc.state, doc);
        }
    }
}
