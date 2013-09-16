@import "DMDomain.j"
@import <CouchResource/COResource.j>
@import <CouchResource/COItemsParent.j>
//import "FixTableColumn.j"

@implementation DMDomainRecordsOutlineController : CPObject
{
    Domain domainRecord @accessors(readonly);
    CPOutlineView domainOutline @accessors(readonly);
    CPPopover popover @accessors;
    CPView  editCell @accessors;
    CPMutableDictionary lookupDomainEntries @accessors;
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

- (void)deleteDomainEntry:(id)sender
{
    var domainEntry = [[self lookupDomainEntries] objectForKey:sender.domainEntry],
        domainRecordAItems = [[[self domainRecord] a] items],
        domainRecordCnameItems = [[[self domainRecord] cname] items],
        domainRecordMxItems = [[[self domainRecord] mx] items];
    [domainRecordAItems removeObject:domainEntry];
    [domainRecordCnameItems removeObject:domainEntry];
    [domainRecordMxItems removeObject:domainEntry];
    [self setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)showPopover:(id)sender
{
    [popover setAnimates:NO];
    console.log(popover);
    var domainEntry = [[self lookupDomainEntries] objectForKey:sender.domainEntry];
    if (![popover isShown])
    {
        var viewDomainEntry = nil;
        if ([domainEntry isKindOfClass:DMDomainA])
        {
            [[popover contentViewController] setView:[self viewDomainA]];
        }
        if ([domainEntry isKindOfClass:DMDomainCname])
        {
            [[popover contentViewController] setView:[self viewDomainCname]];
        }
        if ([domainEntry isKindOfClass:DMDomainMx])
        {
            [[popover contentViewController] setView:[self viewDomainMx]];
        }
        var viewDomainEntry = [[popover contentViewController] view];
        [[viewDomainEntry subviews] enumerateObjectsUsingBlock:function(view) {
            if ([view respondsToSelector:@selector(placeholderString)] && [view placeholderString] != nil)
            {
                var value = @"";
                switch ([view placeholderString])
                {
                case @"host":
                    value = [domainEntry host];
                    break;
                case @"ip":
                    value = [domainEntry ip];
                    break;
                case @"alias":
                    value = [domainEntry alias];
                    break;
                case @"priority":
                    value = [domainEntry priority];
                    break;
                }
                [view setObjectValue:value];
            }
        }];
        [popover showRelativeToRect:nil ofView:sender preferredEdge:nil];
    } else  {
        var viewDomainEntry = [[popover contentViewController] view];
        [[viewDomainEntry subviews] enumerateObjectsUsingBlock:function(view) {
            if ([view respondsToSelector:@selector(placeholderString)] && [view placeholderString] != nil)
            {
                switch ([view placeholderString])
                {
                case @"host":
                    [domainEntry setHost:[view objectValue]];
                    break;
                case @"ip":
                    [domainEntry setIp:[view objectValue]];
                    break;
                case @"alias":
                    [domainEntry setAlias:[view objectValue]];
                    break;
                case @"priority":
                    [domainEntry setPriority:[view objectValue]];
                    break;
                }
            }
        }];
        [popover close];
        [self setLookupForDomainEntries];
        [domainOutline reloadData];
    }
    [domainOutline selectRowIndexes:[CPIndexSet indexSetWithIndex:0] byExtendingSelection:NO];
}
@end


@implementation DMDomainRecordsOutlineController (OutlineProtocol)
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

-(id)outlineView:(id)outlineView dataViewForTableColumn:(id)tableColumn item:(id)item
{
    var view = nil;
    if ([item isKindOfClass:COItemsParent])
    {
        view = [outlineView makeViewWithIdentifier:@"showDomainRecordType" owner:self];
        switch (item.label)
        {
        case @"A":
            [[view textField] setStringValue:[[self domainRecord] a].label];
            break;
        case @"CNAME":
            [[view textField] setStringValue:[[self domainRecord] cname].label];
            break;
        case @"MX":
            [[view textField] setStringValue:[[self domainRecord] mx].label];
            break;
        }
    } else {
        view = [outlineView makeViewWithIdentifier:@"editDomainRecord" owner:self];
        [[view textField] setStringValue:[item objectValueForOutlineColumn:tableColumn]];
        var editButton = [view viewWithTag:1000],
            deleteButton = [view viewWithTag:1010];

        [editButton setTarget:self];
        editButton.domainEntry = item;
        [editButton setAction:@selector(showPopover:)];

        [deleteButton setTarget:self];
        deleteButton.domainEntry = item;
        [deleteButton setAction:@selector(deleteDomainEntry:)];
    }
    return view;
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
