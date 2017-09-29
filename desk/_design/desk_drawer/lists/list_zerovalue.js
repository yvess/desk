function(head, req) {
    provides('json', function() {
        var results = [];
        while (row = getRow()) {
            if (row.value == 0) {
                var data = {};
                data[row.key] = row.value;
                results.push(data);
            }
        }
        send(JSON.stringify(results));
    });
}
