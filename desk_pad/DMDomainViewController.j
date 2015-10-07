@import <AppKit/CPViewController.j>
@import <AppKit/CPEvent.j>
@import <AppKit/CPWebView.j>
@import <AppKit/CPOutlineView.j>
@import <AppKit/CPPopover.j>
@import <CouchResource/COViewController.j>
@import <CouchResource/COArrayController.j>
@import "DMDomain.j"
@import "DMTemplate.j"
@import "DMDomainRecordsOutlineController.j"

@implementation DMDomainViewController : COViewController
{
    @outlet              CPButton addDomainCnameButton;
    @outlet              CPButton addDomainAButton;
    @outlet              CPButton addDomainMxButton;
    @outlet              CPPopUpButton clientsForDomainPopUp;
    @outlet              CPOutlineView domainOutline;
    @outlet              CPPopover popoverDomain;
    @outlet              CPView viewDomainA;
    @outlet              CPView viewDomainCname;
    @outlet              CPView viewDomainMx;
    @outlet              CPPopUpButton tplForDomainPopUp;
    @outlet              CPButton showTplButton;
    @outlet              CPPopover popoverTpl;
    @outlet              CPWebView webviewTpl;

    CPMutableArray        clients;
    CPMutableArray        domainRecordTemplates @accessors;
    CPMutableDictionary   clientLookup;
    CPMutableDictionary   itemLookup @accessors;
    DMDomain              currentDomain @accessors;
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
        itemLookup = [self createLookup];
    }
    return self;
}

- (void)addDomainA:(id)sender
{
    [[[[self currentDomain] a] items] addObject:[[DMDomainA alloc]
        initWithJSObject:{ "host": "new", "ip": "0.0.0.0" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)addDomainCname:(id)sender
{
    [[[[self currentDomain] cname] items] addObject:[[DMDomainCname alloc]
        initWithJSObject:{ "alias": "new", "host": "new" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)addDomainMx:(id)sender
{
    [[[[self currentDomain] mx] items] addObject:[[DMDomainMx alloc]
        initWithJSObject:{ "host": "new", "priority": "10" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
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
        if ([object coId] == [context templateId])
        {
            return true;
        } else {
            return false;
        }
    }
    var templateIndex = [
        domainRecordTemplates indexOfObjectPassingTest:objectPassingFunction
        context:aItem];
    [tplForDomainPopUp selectItemAtIndex:(templateIndex == -1) ? 0 : templateIndex + 1];

    var domainOutlineController = [[DMDomainRecordsOutlineController alloc] initWithDomain:aItem
        domainOutline:domainOutline popover:popoverDomain viewDomainA:viewDomainA
        viewDomainCname:viewDomainCname viewDomainMx:viewDomainMx];
    [domainOutline setDelegate:domainOutlineController];
    [domainOutline setDataSource:domainOutlineController];
    //[domainOutline setRowHeight:28];
    [domainOutline reloadData];
    [self setCurrentDomain:aItem];
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
        var menuItem = [clientsForDomainPopUp itemWithTitle:[item name]];
        [menuItem setRepresentedObject:item];
    }];
    [tplForDomainPopUp addItemWithTitle:@" "];
    [self setDomainRecordTemplates:[DMTemplate all]];
    [[self domainRecordTemplates] enumerateObjectsUsingBlock:function(item) {
        [tplForDomainPopUp addItemWithTitle:[item name]];
        var menuItem = [tplForDomainPopUp itemWithTitle:[item name]];
        [menuItem setRepresentedObject:item];
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
}

- (void)saveModel:(id)sender
{
    var item = [self lastSelectedObject],
        selectedClientId = [[[clientsForDomainPopUp selectedItem] representedObject] coId];
    [item setClientId:selectedClientId];

    var selectedTemplateId = [[[tplForDomainPopUp selectedItem] representedObject] coId];
    [item setTemplateId:selectedTemplateId];
    if ([item coRev])
    {
        [item setState:@"changed"];
    } else {
        [item setState:@"new"];
    }
    [super saveModel:sender];
}

@end
