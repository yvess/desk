function(doc) {
    if (doc.hasOwnProperty('version')) {
        emit(doc.version, doc.type);
    }
    // else {
    //     emit(0, doc.type);
    // }
}
