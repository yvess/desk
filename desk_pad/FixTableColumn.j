@import "DMDns.j"
@import <CouchResource/COResource.j>

@implementation CPTableColumn (FixTableColumn)
- (id)dataViewForRow:(int)aRowIndex
{
    var tableView = [self tableView],
        item = nil;

    if ([tableView isKindOfClass:[CPOutlineView class]])
    {
        item = [tableView itemAtRow:aRowIndex];
    }

    if ([item isKindOfClass:[DMDnsA class]] || [item isKindOfClass:[DMDnsCname class]] || [item isKindOfClass:[DMDnsMx class]])
    {
        var editCell = [[tableView delegate] editCell],
            textfield = [[editCell subviews] objectAtIndex:0],
            button = [[editCell subviews] objectAtIndex:2],
            identifier = [item objectValueForOutlineColumn:@"entry"];
        [textfield setObjectValue:identifier];
        return editCell;
    } else if ([item isKindOfClass:[COItemsParent class]]) {
        var parentCell = [[CPTextField alloc] initWithFrame:[tableView frameOfDataViewAtColumn:0 row:aRowIndex]];
        [parentCell setVerticalAlignment:CPCenterVerticalTextAlignment];
        return parentCell;
    }

    return [self dataView];
}
@end
