@import "DMDns.j"
@import <CouchResource/COResource.j>
@import "FixTableColumn.j"

@implementation DMDnsRecordsOutlineController : CPObject
{
    Dns dnsRecord @accessors(readonly);
    CPOutlineView dnsOutline @accessors(readonly);
    CPPopover popover @accessors;
    CPView  editCell @accessors;
    CPMutableDictionary lookupDnsEntries @accessors;
    CPPopover popover @accessors;
    CPView viewDnsA @accessors;
    CPView viewDnsCname @accessors;
    CPView viewDnsMx @accessors;
}

- (id)initWithDns:(DMDns)aDns dnsOutline:(CPOutlineView)aDnsOutline editCell:(CPView)aEditCell
      popover:(CPPopover)aPopover viewDnsA:(CPView) aViewDnsA viewDnsCname:(CPView) aViewDnsCname viewDnsMx:(CPView) aViewDnsMx
{
    self = [super init];
    if (self)
    {
        dnsRecord = aDns;
        dnsOutline = aDnsOutline;
        popover = aPopover;
        viewDnsA = aViewDnsA;
        viewDnsCname = aViewDnsCname;
        viewDnsMx = aViewDnsMx;
        [self setEditCell:aEditCell];
        [self setLookupForDnsEntries];
    }
    return self;
}

- (CPMutableDictionary)setLookupForDnsEntries
{
    lookupDnsEntries = [[CPMutableDictionary alloc] init];
    var dnsEntries = [[CPMutableArray alloc] initWithArray:[[[self dnsRecord] a] items]];
    [dnsEntries addObjectsFromArray:[[[self dnsRecord] cname] items]];
    [dnsEntries addObjectsFromArray:[[[self dnsRecord] mx] items]];
    [dnsEntries enumerateObjectsUsingBlock:function(item) {
        [lookupDnsEntries setObject:item forKey:[item objectValueForOutlineColumn:@"entry"]];
    }];
}

- (int)outlineView:(CPOutlineView)outlineView numberOfChildrenOfItem:(id)item
{
    var count = 3; // for root îtem
    if (item != nil)
    {
        if ([item respondsToSelector:CPSelectorFromString(@"items")])
        {
            count = [[item items] count];
        } else {
            count = 0;
        }
    }
    return count;
}

- (id)outlineView:(CPOutlineView)outlineView child:(int)index ofItem:(id)item
{
    var result = nil;
    if (item == nil)
    {
        switch (index)
        {
        case 0:
            result = [[self dnsRecord] a];
            break;
        case 1:
            result = [[self dnsRecord] cname];
            break;
        case 2:
            result = [[self dnsRecord] mx];
            break;
        }
    } else {
        result = [[item items] objectAtIndex: index];
    }
    return result;
}

- (BOOL)outlineView:(CPOutlineView)outlineView isItemExpandable:(id)item
{
    var numberOfChilds = [self outlineView:outlineView numberOfChildrenOfItem:item];
    if (numberOfChilds == 0)
    {
        var rows = [outlineView rowsInRect:[outlineView visibleRect]];
    }
    return [self outlineView:outlineView numberOfChildrenOfItem:item] > 0;
}

- (id)outlineView:(CPOutlineView)outlineView objectValueForTableColumn:(CPTableColumn)tableColumn byItem:(id)item
{
    var value = @"";
    if ([tableColumn identifier])
    {
        value = (item == nil) ? @"" : [item objectValueForOutlineColumn: tableColumn];
    }
    return value;
}

- (BOOL)outlineView:(CPOutlineView)outlineView shouldSelectTableColumn:(CPTableColumn)tableColumn
{
    return NO;
}
@end
