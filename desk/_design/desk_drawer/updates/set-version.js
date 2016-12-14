function(doc, req) {
    var new_version = req.query.version;
    var old_version = null;
    if (doc.hasOwnProperty('version')) {
        old_version = doc.version;
    }
    doc.version = parseInt(new_version);
    var changed = doc._id + ":" + old_version + ":" + new_version;
    return [doc, toJSON(changed)];
}
