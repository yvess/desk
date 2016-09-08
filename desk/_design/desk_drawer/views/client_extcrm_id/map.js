function(doc) {
    if (doc.type == 'client') {
        emit(doc.extcrm_id, doc._id);
    }
}
