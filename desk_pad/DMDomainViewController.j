@import <AppKit/CPViewController.j>
@import <AppKit/CPEvent.j>
@import <AppKit/CPWebView.j>
@import <CouchResource/COViewController.j>
@import <CouchResource/COArrayController.j>
@import "DMDomain.j"
@import "DMTemplate.j"
@import "DMDomainRecordsOutlineController.j"

@implementation DMEditCellView : CPView
{
}

- (void)setObjectValue:(id)anObject
{
    var textfield = [[self subviews] objectAtIndex:0]; // this is the textfield
    [textfield setObjectValue:anObject];
    var button_edit = [[self subviews] objectAtIndex:2],
        button_del = [[self subviews] objectAtIndex:1];

    [button_edit setTarget:self];
    button_edit.domainEntry = anObject;
    [button_edit setAction:@selector(showPopover:)];

    [button_del setTarget:self];
    button_del.domainEntry = anObject;
    [button_del setAction:@selector(deleteDomainEntry:)];
}

- (id)delegate
{
    return nil;
}

- (void)deleteDomainEntry:(id)sender
{
    var outlineView = [[sender superview] superview],
        outlineController = [outlineView delegate],
        domainEntry = [[outlineController lookupDomainEntries] objectForKey:sender.domainEntry],
        domainRecordAItems = [[[outlineController domainRecord] a] items],
        domainRecordCnameItems = [[[outlineController domainRecord] cname] items],
        domainRecordMxItems = [[[outlineController domainRecord] mx] items];
    [domainRecordAItems removeObject:domainEntry];
    [domainRecordCnameItems removeObject:domainEntry];
    [domainRecordMxItems removeObject:domainEntry];
    [outlineController setLookupForDomainEntries];
    [outlineView reloadData];
}

- (void)showPopover:(id)sender
{
    var outlineView = [[sender superview] superview],
        outlineController = [outlineView delegate],
        popover = [outlineController popover];
    [popover setAnimates:NO];
    var domainEntry = [[outlineController lookupDomainEntries] objectForKey:sender.domainEntry];
    if (![popover isShown])
    {
        var viewDomainEntry = nil;
        if ([domainEntry isKindOfClass:DMDomainA])
        {
            [[popover contentViewController] setView:[outlineController viewDomainA]];
        }
        if ([domainEntry isKindOfClass:DMDomainCname])
        {
            [[popover contentViewController] setView:[outlineController viewDomainCname]];
        }
        if ([domainEntry isKindOfClass:DMDomainMx])
        {
            [[popover contentViewController] setView:[outlineController viewDomainMx]];
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
        [outlineController setLookupForDomainEntries];
        [outlineView reloadData];
    }
    [outlineView selectRowIndexes:[CPIndexSet indexSetWithIndex:0] byExtendingSelection:NO];
}
@end

@implementation DMDomainViewController : COViewController
{
    @outlet              CPButton addDomainCnameButton;
    @outlet              CPButton addDomainAButton;
    @outlet              CPButton addDomainMxButton;
    @outlet              CPPopUpButton clientsForDomainPopUp;
    @outlet              CPOutlineView aDomainOutline;
    @outlet              DMEditCellView editButtonCell;
    @outlet              CPPopover popoverDomain;
    @outlet              CPView viewDomainA;
    @outlet              CPView viewDomainCname;
    @outlet              CPView viewDomainMx;
    @outlet              CPPopUpButton tplForDomainPopUp;
    @outlet              CPButton showTplButton;
    @outlet              CPPopover popoverTpl;
    @outlet              CPWebView webviewTpl;


    //CPMutableArray        domain;
    CPMutableArray        clients;
    CPMutableArray        domainRecordTemplates @accessors;
    CPMutableDictionary   clientLookup;
    DMDomain                 currentDomain @accessors;
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
      modelClass: (CPObject) aModelClass
      clients: (CPMutableArray) aClientsArray
      clientLookup: (CPMutableDictionary) aClientLookup
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass];
    if (self)
    {
        clients = aClientsArray;
        clientLookup = aClientLookup;
    }
    return self;
}


/*- (void)saveDomain:(id)sender
{
    var aDomain = [[aDomainArrayController selectedObjects] lastObject];
    if (![aDomain coId])
    {
        [aDomain setCoId:[[aDomain class] couchId:aDomain]];
    }
    var selectedClientId = [[clients objectAtIndex:[clientsForDomainPopUp indexOfSelectedItem]] coId];
    [aDomain setClientId:selectedClientId];
    [aDomain save];
}*/


- (void)addDomainA:(id)sender
{
    [[[[self currentDomain] a] items] addObject:[[DMDomainA alloc] initWithJSObject:{ "host": "new", "ip": "0.0.0.0" }] ];
    [[aDomainOutline delegate] setLookupForDomainEntries];
    [aDomainOutline reloadData];
}

- (void)addDomainCname:(id)sender
{
    [[[[self currentDomain] cname] items] addObject:[[DMDomainCname alloc] initWithJSObject:{ "alias": "new", "host": "new" }] ];
    [[aDomainOutline delegate] setLookupForDomainEntries];
    [aDomainOutline reloadData];
}

- (void)addDomainMx:(id)sender
{
    [[[[self currentDomain] mx] items] addObject:[[DMDomainMx alloc] initWithJSObject:{ "host": "new", "priority": "10" }] ];
    [[aDomainOutline delegate] setLookupForDomainEntries];
    [aDomainOutline reloadData];
}

- (void)showTpl:(id)sender
{
    var coId = [[[tplForDomainPopUp selectedItem] representedObject] coId];
    [webviewTpl setMainFrameURL:[CPString stringWithFormat:@"/show/%@", coId]];
    [popoverTpl setAnimates:NO];
    if (![popoverTpl isShown])
    {
        [[popoverTpl contentViewController] setView:webviewTpl];
        [popoverTpl showRelativeToRect:nil ofView:sender preferredEdge:nil];
    } else {
        [popoverTpl close];
    }
}

- (void)updateDomainOutline:(id) aItem
{
    [popoverDomain close];
    var clientIndex = [clients indexOfObject:[clientLookup objectForKey:[aItem clientId]]];
    [clientsForDomainPopUp selectItemAtIndex:clientIndex];
    var objectPassingFunction = function(object, index, context) {
        if ([object coId] == [context templateId]) {
            return true;
        } else {
            return false;
        }
    }
    var templateIndex = [domainRecordTemplates
            indexOfObjectPassingTest: objectPassingFunction
            context:aItem
        ];
    [tplForDomainPopUp selectItemAtIndex:(templateIndex == -1) ? 0 : templateIndex + 1];

    var domainOutlineController = [[DMDomainRecordsOutlineController alloc] initWithDomain:aItem domainOutline:aDomainOutline
        editCell:editButtonCell popover:popoverDomain viewDomainA:viewDomainA viewDomainCname:viewDomainCname viewDomainMx:viewDomainMx];
    [aDomainOutline setDataSource:domainOutlineController];
    [aDomainOutline setDelegate:domainOutlineController];
    [aDomainOutline setRowHeight:28];
    [aDomainOutline reloadData];
    [self setCurrentDomain:aItem];
    console.log("setCurrentDomain", aItem);
}

- (void)observeValueForKeyPath:(CPString) aKeyPath
        ofObject:(id) anObject
        change:(CPDictionary) aChange
        context:(id) aContext
{
    var aItem = [[anObject arrangedObjects] objectAtIndex:[anObject selectionIndex]],
        new_value = [aChange valueForKey:@"CPKeyValueChangeNewKey"],
        old_value = [aChange valueForKey:@"CPKeyValueChangeOldKey"];

    if ([aItem class] == [self modelClass])
    {
        [aItem isSelected];
        [self updateDomainOutline:aItem];
    }
}

- (void)viewDidLoad
{
    [super viewDidLoad];
    [clients enumerateObjectsUsingBlock:function(item) {
        [clientsForDomainPopUp addItemWithTitle:[item name]];
    }];
    [tplForDomainPopUp addItemWithTitle:@" "];
    [self setDomainRecordTemplates:[DMTemplate all]];
    [[self domainRecordTemplates] enumerateObjectsUsingBlock:function(item) {
        [tplForDomainPopUp addItemWithTitle:[item name]];
        var menuItem = [tplForDomainPopUp itemWithTitle:[item name]];
        [menuItem setRepresentedObject: item];
    }];
    [arrayController addObserver:self forKeyPath:@"selection.domain" options:nil context:@"domain"];
    var last = [self lastSelectedObject];
    if (last != nil)
        [self updateDomainOutline:[self lastSelectedObject]];

    [addDomainAButton setAction:@selector(addDomainA:)];
    [addDomainAButton setTarget:self];

    [addDomainCnameButton setAction:@selector(addDomainCname:)];
    [addDomainCnameButton setTarget:self];

    [addDomainMxButton setAction:@selector(addDomainMx:)];
    [addDomainMxButton setTarget:self];

    [showTplButton setAction:@selector(showTpl:)];
    [showTplButton setTarget:self];

    //[saveDomainButton setTarget:self];
    //[saveDomainButton setAction:@selector(saveDomain:)]
}

- (void)saveModel:(id)sender
{
    var item = [self lastSelectedObject];
    if (![item coId])
    {
        [item setCoId:[[item class] couchId:item]];
    }
    var selectedClientId = [[clients objectAtIndex:[clientsForDomainPopUp indexOfSelectedItem]] coId];
    [item setClientId:selectedClientId];

    var selectedTemplateId = [[[tplForDomainPopUp selectedItem] representedObject] coId];
    [item setTemplateId:selectedTemplateId];
    [item setState:@"new"];

    [item save];
}

@end
