function(doc) {
    if (doc.type == 'order' && doc.state == 'new') {
        emit(doc._id, doc.editor);
    }
}