function(doc, req) {
    if (doc.type == 'order' && doc.state == 'new') {
        return true;
    }
    return false;
}
