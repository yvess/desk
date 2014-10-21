function(doc) {
    if (doc.type == 'project') {
        emit([doc._id, 0], {
            _id: doc._id
        });
    }
}