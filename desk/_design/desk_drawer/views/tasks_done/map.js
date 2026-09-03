function(doc) {
    if (doc.type == 'task' && doc.state == 'done')  {
        emit(doc._id, doc._rev);
    }
}
