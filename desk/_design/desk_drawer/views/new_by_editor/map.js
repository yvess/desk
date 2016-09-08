function(doc) {
    if (doc.type != 'order') {
        if (['new', 'changed', 'delete'].indexOf(doc.state) >= 0) {
            emit(doc.editor, doc._id);
        }
    }
}
