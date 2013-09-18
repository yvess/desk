function(doc, req) {
    if (doc.type == 'task' && doc.state != 'done') {
        return true;
    }
    return false;
}