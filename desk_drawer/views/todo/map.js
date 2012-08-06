
function (doc) {
    if ((doc.state && doc.state == "updated") || (doc.state && doc.state == "created")) {
        if (doc.type != "queue") {
            emit(doc.state, doc);
        }
    }
}