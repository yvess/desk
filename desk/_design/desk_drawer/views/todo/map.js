function(doc) {
    if ((doc.state && doc.state == 'changed') || (doc.state && doc.state == 'new')) {
        if (doc.type != 'order') {
            emit(doc.state, doc);
        }
    }
}