function(doc) {
    if (doc.type == 'inspector') {
        for (var i = 0; i < doc.items_not_found.length; i++) {
            emit(doc.items_not_found[i].domain, 0);
        }
        for (var j = 0; j < doc.items.length; j++) {
            emit(doc.items[j].domain, 1);
        }
    }
}
