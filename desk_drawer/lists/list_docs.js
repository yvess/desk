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

               results.push(row.doc);
               // dataItem = {};

        }
        // make sure to stringify the results :)
        send(JSON.stringify(results));
    });
}