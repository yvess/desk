function(doc) {
    if (doc.type == 'task' && doc.state == 'new')  {
        emit(doc._id, doc._rev);
    }
}
