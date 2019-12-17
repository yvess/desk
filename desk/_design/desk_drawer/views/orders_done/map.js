function(doc) {
    if (doc.type == 'order') {
        if (doc.state == 'done' || doc.state == 'error') {
            emit(doc._id);
        }
    }
}
