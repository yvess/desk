function(doc, req) {
    var editor = req.userCtx.name;
    doc['editor'] = editor;
    var message = 'added editor';
    return [doc, message];
}