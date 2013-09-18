function(doc, req) {
    if (doc.type == 'order' && doc.state != 'done') {
        return true;
    }
    return false;
}