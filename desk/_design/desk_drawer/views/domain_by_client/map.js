function(doc) {
    if (doc.type == 'domain' && doc.state.indexOf('delete') < 0) {
        emit(doc.client_id, doc._id);
    }
}
