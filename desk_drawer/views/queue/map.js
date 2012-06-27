function(doc) {
  if (doc.type == "queue") {
    emit(doc._id, doc._rev);
  }
};