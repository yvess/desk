function(doc) {
    var completed_states = ['done', 'done_checked', 'active', 'deleted']
    if (doc.hasOwnProperty('state') && completed_states.indexOf(doc.state) == -1)  {
        emit(doc._id, doc._rev);
    }
}
