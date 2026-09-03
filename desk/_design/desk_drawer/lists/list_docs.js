function(head, req) {
    provides('json', function() {
        var results = [];
        var dataItem = {};
        while (row = getRow()) {
            if (row && row.hasOwnProperty('doc')) {
                row.doc.coId = row.doc._id;
                row.doc.coRev = row.doc._rev;
                if (row.doc.hasOwnProperty('_attachments')) {
                    row.doc.coAttachments = row.doc._attachments;
                }
                if (true) {
                    if (dataItem != {} && dataItem.client_id) {
                        dataItem.client = row.doc;
                    } else {
                        dataItem = row.doc;
                    }
                    results.push(dataItem);
                    dataItem = {};
                }
            }
        }
        send(JSON.stringify(results));
    });
}
