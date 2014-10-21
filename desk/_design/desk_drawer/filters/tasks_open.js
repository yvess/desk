function(doc, req) {
    if (doc.type == 'task' && doc.state == 'new') {
        return true;
    }
    return false;
}
