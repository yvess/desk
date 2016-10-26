function(doc, req) {
    var new_state = req.query.state;
    old_state = doc['state'];
    doc['state'] = new_state;
    var changed = doc._id + ":" + old_state + ":" + new_state;
    return [doc, toJSON(changed)];
}
