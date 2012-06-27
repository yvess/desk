function (doc) {
    if (doc.type == "project") {
        emit([doc._id, 0], {_id:doc._id});
        //if (doc.client_id) {
        //    emit([doc._id, 1, doc.client_id], {_id: doc.client_id});
        //}
    }
}