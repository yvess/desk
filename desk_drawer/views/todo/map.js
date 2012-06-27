function(doc) {
  if (doc.state && doc.state == "new") {
    emit(doc.state, doc);
  }
};