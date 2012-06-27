function(doc) {
  if (doc.type == "client") {
    emit(doc._id, doc._rev);
  }
};