function(doc) {
    if (doc.type == 'work_time') {
        emit([doc.project_id, doc.date], 1);
    }
}