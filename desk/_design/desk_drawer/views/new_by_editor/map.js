function(doc) {
    if (doc.state == 'new' && doc.type != 'order' && doc.type != 'task') {
        emit(doc.editor, doc._id);
    }
}