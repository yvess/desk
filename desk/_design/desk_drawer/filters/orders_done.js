function(doc, req) {
    if (doc.type == 'order') {
        if (doc.state == 'done' || doc.state == 'failed' ) {
            return true;
        }
    }
    return false;
}
