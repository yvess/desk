function(doc) {
    if (doc.type == 'order') {
        emit(doc.date, doc._id);
    }
}
