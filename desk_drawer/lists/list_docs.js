function (head, req) {
    // specify that we're providing a JSON response
    provides('json', function() {
        // create an array for our result set
        var results = [];
        var dataItem = {};
        while (row = getRow()) {
            row.doc.coId = row.doc._id;
            row.doc.coRev = row.doc._rev;
            if (row.doc.hasOwnProperty("_attachments")) {
                row.doc.coAttachments = row.doc._attachments;
            }
            /*if (row.doc.client_id) {
                dataItem = row.doc;
            }*/
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
        // make sure to stringify the results :)
        send(JSON.stringify(results));
    });
}