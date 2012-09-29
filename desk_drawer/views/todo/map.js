
function (doc) {
    if ((doc.state && doc.state == "changed") || (doc.state && doc.state == "new")) {
        if (doc.type != "queue") {
            emit(doc.state, doc);
        }
    }
}