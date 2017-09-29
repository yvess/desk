function(doc) {
    if (doc.type == 'inspector') {
        var domains_not_found = []
        for each (item in doc.items_not_found) {
            emit(item.domain, 0);
        }
        for each (item in doc.items) {
            emit(item.domain, 1);
        }
    }
}
