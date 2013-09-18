function(doc, req) {
    delete doc._id;
    delete doc._rev;
    delete doc._revisions;
    delete doc.type;
    delete doc.name;
    delete doc.template_type;
    var html = '<div><pre>' + JSON.stringify(doc, null, 4) + '<\/pre><\/div>';
    return html;
}