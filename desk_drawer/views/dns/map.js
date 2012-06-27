function(doc) {
  if (doc.type == "dns") {
    emit(doc._id, doc._rev);
  }
};