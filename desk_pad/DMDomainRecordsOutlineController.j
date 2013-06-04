@import "DMDomain.j"
@import <CouchResource/COResource.j>
@import "FixTableColumn.j"

@implementation DMDomainRecordsOutlineController : CPObject
{
    Domain domainRecord @accessors(readonly);
    CPOutlineView domainOutline @accessors(readonly);
    CPPopover popover @accessors;
    CPView  editCell @accessors;
    CPMutableDictionary lookupDomainEntries @accessors;
    CPPopover popover @accessors;
    CPView viewDomainA @accessors;
    CPView viewDomainCname @accessors;
    CPView viewDomainMx @accessors;
}

- (id)initWithDomain:(DMDomain)aDomain domainOutline:(CPOutlineView)aDomainOutline editCell:(CPView)aEditCell
      popover:(CPPopover)aPopover viewDomainA:(CPView) aViewDomainA viewDomainCname:(CPView) aViewDomainCname viewDomainMx:(CPView) aViewDomainMx
{
    self = [super init];
    if (self)
    {
        domainRecord = aDomain;
        domainOutline = aDomainOutline;
        popover = aPopover;
        viewDomainA = aViewDomainA;
        viewDomainCname = aViewDomainCname;
        viewDomainMx = aViewDomainMx;
        [self setEditCell:aEditCell];
        [self setLookupForDomainEntries];
    }
    return self;
}

- (CPMutableDictionary)setLookupForDomainEntries
{
    lookupDomainEntries = [[CPMutableDictionary alloc] init];
    var domainEntries = [[CPMutableArray alloc] initWithArray:[[[self domainRecord] a] items]];
    [domainEntries addObjectsFromArray:[[[self domainRecord] cname] items]];
    [domainEntries addObjectsFromArray:[[[self domainRecord] mx] items]];
    [domainEntries enumerateObjectsUsingBlock:function(item) {
        [lookupDomainEntries setObject:item forKey:[item objectValueForOutlineColumn:@"entry"]];
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
            result = [[self domainRecord] a];
            break;
        case 1:
            result = [[self domainRecord] cname];
            break;
        case 2:
            result = [[self domainRecord] mx];
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
