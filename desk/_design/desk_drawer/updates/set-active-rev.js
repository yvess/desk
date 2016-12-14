function(doc, req) {
    var new_active_rev = req.query.active_rev;
    if (doc.hasOwnProperty('active_rev')) {
        doc.prev_active_rev = doc.active_rev;
    }
    doc.active_rev = new_active_rev;
    return [doc, "updated active_rev to: " + new_active_rev];
}
