@import <AppKit/CPViewController.j>
@import <AppKit/CPEvent.j>
@import <AppKit/CPWebView.j>
@import <CouchResource/COViewController.j>
@import <CouchResource/COArrayController.j>
@import "DMDns.j"
@import "DMTemplate.j"
@import "DMDnsRecordsOutlineController.j"

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
    button_edit.dnsEntry = anObject;
    [button_edit setAction:@selector(showPopover:)];

    [button_del setTarget:self];
    button_del.dnsEntry = anObject;
    [button_del setAction:@selector(deleteDnsEntry:)];
}

- (id)delegate
{
    return nil;
}

- (void)deleteDnsEntry:(id)sender
{
    var outlineView = [[sender superview] superview],
        outlineController = [outlineView delegate],
        dnsEntry = [[outlineController lookupDnsEntries] objectForKey:sender.dnsEntry],
        dnsRecordAItems = [[[outlineController dnsRecord] a] items],
        dnsRecordCnameItems = [[[outlineController dnsRecord] cname] items],
        dnsRecordMxItems = [[[outlineController dnsRecord] mx] items];
    [dnsRecordAItems removeObject:dnsEntry];
    [dnsRecordCnameItems removeObject:dnsEntry];
    [dnsRecordMxItems removeObject:dnsEntry];
    [outlineController setLookupForDnsEntries];
    [outlineView reloadData];
}

- (void)showPopover:(id)sender
{
    var outlineView = [[sender superview] superview],
        outlineController = [outlineView delegate],
        popover = [outlineController popover];
    [popover setAnimates:NO];
    var dnsEntry = [[outlineController lookupDnsEntries] objectForKey:sender.dnsEntry];
    if (![popover isShown])
    {
        var viewDnsEntry = nil;
        if ([dnsEntry isKindOfClass:DMDnsA])
        {
            [[popover contentViewController] setView:[outlineController viewDnsA]];
        }
        if ([dnsEntry isKindOfClass:DMDnsCname])
        {
            [[popover contentViewController] setView:[outlineController viewDnsCname]];
        }
        if ([dnsEntry isKindOfClass:DMDnsMx])
        {
            [[popover contentViewController] setView:[outlineController viewDnsMx]];
        }
        var viewDnsEntry = [[popover contentViewController] view];
        [[viewDnsEntry subviews] enumerateObjectsUsingBlock:function(view) {
            if ([view respondsToSelector:@selector(placeholderString)] && [view placeholderString] != nil)
            {
                var value = @"";
                switch ([view placeholderString])
                {
                case @"host":
                    value = [dnsEntry host];
                    break;
                case @"ip":
                    value = [dnsEntry ip];
                    break;
                case @"alias":
                    value = [dnsEntry alias];
                    break;
                case @"priority":
                    value = [dnsEntry priority];
                    break;
                }
                [view setObjectValue:value];
            }
        }];
        [popover showRelativeToRect:nil ofView:sender preferredEdge:nil];
    } else  {
        var viewDnsEntry = [[popover contentViewController] view];
        [[viewDnsEntry subviews] enumerateObjectsUsingBlock:function(view) {
            if ([view respondsToSelector:@selector(placeholderString)] && [view placeholderString] != nil)
            {
                switch ([view placeholderString])
                {
                case @"host":
                    [dnsEntry setHost:[view objectValue]];
                    break;
                case @"ip":
                    [dnsEntry setIp:[view objectValue]];
                    break;
                case @"alias":
                    [dnsEntry setAlias:[view objectValue]];
                    break;
                case @"priority":
                    [dnsEntry setPriority:[view objectValue]];
                    break;
                }
            }
        }];
        [popover close];
        [outlineController setLookupForDnsEntries];
        [outlineView reloadData];
    }
    [outlineView selectRowIndexes:[CPIndexSet indexSetWithIndex:0] byExtendingSelection:NO];
}
@end

@implementation DMDnsViewController : COViewController
{
    IBOutlet              CPButton addDnsCnameButton;
    IBOutlet              CPButton addDnsAButton;
    IBOutlet              CPButton addDnsMxButton;
    IBOutlet              CPPopUpButton clientsForDnsPopUp;
    IBOutlet              CPOutlineView aDnsOutline;
    IBOutlet              DMEditCellView editButtonCell;
    IBOutlet              CPPopover popoverDns;
    IBOutlet              CPView viewDnsA;
    IBOutlet              CPView viewDnsCname;
    IBOutlet              CPView viewDnsMx;
    IBOutlet              CPPopUpButton tplForDnsPopUp;
    IBOutlet              CPButton showTplButton;
    IBOutlet              CPPopover popoverTpl;
    IBOutlet              CPWebView webviewTpl;


    //CPMutableArray        dns;
    CPMutableArray        clients;
    CPMutableArray        dnsRecordTemplates @accessors;
    CPMutableDictionary   clientLookup;
    DMDns                 currentDns @accessors;
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


/*- (void)saveDns:(id)sender
{
    var aDns = [[aDnsArrayController selectedObjects] lastObject];
    if (![aDns coId])
    {
        [aDns setCoId:[[aDns class] couchId:aDns]];
    }
    var selectedClientId = [[clients objectAtIndex:[clientsForDnsPopUp indexOfSelectedItem]] coId];
    [aDns setClientId:selectedClientId];
    [aDns save];
}*/


- (void)addDnsA:(id)sender
{
    [[[[self currentDns] a] items] addObject:[[DMDnsA alloc] initWithJSObject:{ "host": "new", "ip": "0.0.0.0" }] ];
    [[aDnsOutline delegate] setLookupForDnsEntries];
    [aDnsOutline reloadData];
}

- (void)addDnsCname:(id)sender
{
    [[[[self currentDns] cname] items] addObject:[[DMDnsCname alloc] initWithJSObject:{ "alias": "new", "host": "new" }] ];
    [[aDnsOutline delegate] setLookupForDnsEntries];
    [aDnsOutline reloadData];
}

- (void)addDnsMx:(id)sender
{
    [[[[self currentDns] mx] items] addObject:[[DMDnsMx alloc] initWithJSObject:{ "host": "new", "priority": "10" }] ];
    [[aDnsOutline delegate] setLookupForDnsEntries];
    [aDnsOutline reloadData];
}

- (void)showTpl:(id)sender
{
    var coId = [[[tplForDnsPopUp selectedItem] representedObject] coId];
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

- (void)updateDnsOutline:(id) aItem
{
    [popoverDns close];
    var clientIndex = [clients indexOfObject:[clientLookup objectForKey:[aItem clientId]]];
    [clientsForDnsPopUp selectItemAtIndex:clientIndex];
    var objectPassingFunction = function(object, index, context) {
        if ([object coId] == [context templateId]) {
            return true;
        } else {
            return false;
        }
    }
    var templateIndex = [dnsRecordTemplates
            indexOfObjectPassingTest: objectPassingFunction
            context:aItem
        ];
    [tplForDnsPopUp selectItemAtIndex:(templateIndex == -1) ? 0 : templateIndex + 1];

    var dnsOutlineController = [[DMDnsRecordsOutlineController alloc] initWithDns:aItem dnsOutline:aDnsOutline
        editCell:editButtonCell popover:popoverDns viewDnsA:viewDnsA viewDnsCname:viewDnsCname viewDnsMx:viewDnsMx];
    [aDnsOutline setDataSource:dnsOutlineController];
    [aDnsOutline setDelegate:dnsOutlineController];
    [aDnsOutline setRowHeight:28];
    [aDnsOutline reloadData];
    [self setCurrentDns:aItem];
    console.log("setCurrentDns", aItem);
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
        [self updateDnsOutline:aItem];
    }
}

- (void)viewDidLoad
{
    [super viewDidLoad];
    [clients enumerateObjectsUsingBlock:function(item) {
        [clientsForDnsPopUp addItemWithTitle:[item name]];
    }];
    [tplForDnsPopUp addItemWithTitle:@" "];
    [self setDnsRecordTemplates:[DMTemplate all]];
    console.log("[DMTemplate all]", [[DMTemplate all] className]);
    [[self dnsRecordTemplates] enumerateObjectsUsingBlock:function(item) {
        [tplForDnsPopUp addItemWithTitle:[item name]];
        var menuItem = [tplForDnsPopUp itemWithTitle:[item name]];
        [menuItem setRepresentedObject: item];
    }];
    [arrayController addObserver:self forKeyPath:@"selection.domain" options:nil context:@"domain"];
    [self updateDnsOutline:[self lastSelectedObject]];

    [addDnsAButton setAction:@selector(addDnsA:)];
    [addDnsAButton setTarget:self];

    [addDnsCnameButton setAction:@selector(addDnsCname:)];
    [addDnsCnameButton setTarget:self];

    [addDnsMxButton setAction:@selector(addDnsMx:)];
    [addDnsMxButton setTarget:self];

    [showTplButton setAction:@selector(showTpl:)];
    [showTplButton setTarget:self];


    //[saveDnsButton setTarget:self];
    //[saveDnsButton setAction:@selector(saveDns:)]
}

- (void)saveModel:(id)sender
{
    var item = [self lastSelectedObject];
    if (![item coId])
    {
        [item setCoId:[[item class] couchId:item]];
    }
    var selectedClientId = [[clients objectAtIndex:[clientsForDnsPopUp indexOfSelectedItem]] coId];
    [item setClientId:selectedClientId];

    var selectedTemplateId = [[[tplForDnsPopUp selectedItem] representedObject] coId];
    [item setTemplateId:selectedTemplateId];
    [item setState:@"new"];

    [item save];
}

@end
