function(doc, req) {
    var editor = req.userCtx.name;
    doc['editor'] = editor;
    if (doc['state'] == 'new_pre') {
        doc['state'] = 'new';
    }
    var message = 'added editor';
    return [doc, message];
}
