function(doc, req) {
    if (doc.type == 'order') {
        if (doc.state == 'done' || doc.state == 'error' ) {
            return true;
        }
    }
    return false;
}
