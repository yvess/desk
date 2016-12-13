@import <AppKit/CPViewController.j>
@import <AppKit/CPEvent.j>
@import <AppKit/CPWebView.j>
@import <AppKit/CPOutlineView.j>
@import <AppKit/CPPopover.j>
@import <CouchResource/COViewController.j>
@import "DMDomain.j"
@import "DMTemplate.j"
@import "DMDomainRecordsOutlineController.j"

@implementation DMDomainViewController : COViewController
{
    @outlet              CPButton addRecordButton;
    @outlet              CPPopUpButton recordPopUp;
    @outlet              CPPopUpButton clientsForDomainPopUp;
    @outlet              CPOutlineView domainOutline;
    @outlet              CPPopover popoverDomain;
    @outlet              CPView viewDomainA;
    @outlet              CPView viewDomainAaaa;
    @outlet              CPView viewDomainCname;
    @outlet              CPView viewDomainMx;
    @outlet              CPView viewDomainTxt;
    @outlet              CPView viewDomainSrv;
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
      growlCenter: (TNGrowlCenter) aGrowlCenter
      clients: (CPMutableArray) aClientsArray
      clientLookup: (CPMutableDictionary) aClientLookup
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass growlCenter:aGrowlCenter];
    if (self)
    {
        clients = aClientsArray;
        clientLookup = aClientLookup;
        itemLookup = [self createLookup];
        items = [modelClass allWithParams:@{} withPath:@"/domains_by_name"];
    }
    return self;
}

- (void)reloadItems
{
    [self setItems:[modelClass allWithParams:@{} withPath:@"/domains_by_name"]];
}

- (void)addRecord:(id)sender
{
    var recordType = [recordPopUp titleOfSelectedItem];
    switch (recordType)
    {
    case @"A":
        [self addDomainA];
        break;
    case @"AAAA":
        [self addDomainAaaa];
        break;
    case @"CNAME":
        [self addDomainCname];
        break;
    case @"MX":
        [self addDomainMx];
        break;
    case @"TXT":
        [self addDomainTxt];
        break;
    case @"SRV":
        [self addDomainSrv];
        break;
    }
}

- (void)addDomainA
{
    [[[[self currentDomain] a] items] addObject:[[DMDomainA alloc]
        initWithJSObject:{ "host": "new", "ip": "0.0.0.0" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}


- (void)addDomainAaaa
{
    [[[[self currentDomain] aaaa] items] addObject:[[DMDomainAaaa alloc]
        initWithJSObject:{ "host": "new", "ipv6": "aaaa:aaaa:aaaa:aaaa::1" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)addDomainCname
{
    [[[[self currentDomain] cname] items] addObject:[[DMDomainCname alloc]
        initWithJSObject:{ "alias": "new", "host": "new" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)addDomainMx
{
    [[[[self currentDomain] mx] items] addObject:[[DMDomainMx alloc]
        initWithJSObject:{ "host": "new", "priority": 10 }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)addDomainTxt
{
    [[[[self currentDomain] txt] items] addObject:[[DMDomainTxt alloc]
        initWithJSObject:{ "name": "new", "content": "info" }] ];
    [[domainOutline delegate] setLookupForDomainEntries];
    [domainOutline reloadData];
}

- (void)addDomainSrv
{
    [[[[self currentDomain] srv] items] addObject:[[DMDomainSrv alloc]
        initWithJSObject:{
            "name": "_service._proto.name.",
            "priority": 10,
            "weight": 10,
            "port": 8080,
            "targethost": "my.server." }
        ]];
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
        domainOutline:domainOutline popover:popoverDomain
        viewRecordTypes: @{
            @"DMDomainA":viewDomainA, @"DMDomainAaaa":viewDomainAaaa,
            @"DMDomainCname":viewDomainCname, @"DMDomainMx":viewDomainMx,
            @"DMDomainTxt":viewDomainTxt,
            @"DMDomainSrv":viewDomainSrv
        }];
    [domainOutline setDelegate:domainOutlineController];
    [domainOutline setDataSource:domainOutlineController];
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

- (void)awakeFromCib
{
    [window.popovers addObject:popoverDomain];
    [window.popovers addObject:popoverTpl];
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
    [[CPNotificationCenter defaultCenter] addObserver:self
        selector:@selector(domainWasRemoved:)
            name:@"DMRemoveTableRow"
          object:nil
    ];
    var last = [self lastSelectedObject];
    if (last != nil)
        [self updateDomainOutline:[self lastSelectedObject]];

    [recordPopUp selectItemWithTitle:@"A"];
    [addRecordButton setAction:@selector(addRecord:)];
    [addRecordButton setTarget:self];

    [showTplButton setAction:@selector(showTpl:)];
    [showTplButton setTarget:self];
}

- (void)domainWasRemoved:(CPNotification)notification
{
    var domainToDelete = [notification object];
    if ([domainToDelete className] == @"DMDomain")
    {
        domainToDelete.state = @"delete";
        var message = [CPString stringWithFormat:@"domain: %@ \nis scheduled for deletion\nsend order for execution", domainToDelete.domain];
        [self.growlCenter pushNotificationWithTitle:@"deleted" message:message];
    }
}

- (void)saveModel:(id)sender
{
    var item = [self lastSelectedObject],
        selectedClientId = [[[clientsForDomainPopUp selectedItem] representedObject] coId];
    [item setClientId:selectedClientId];

    var selectedTemplateId = [[[tplForDomainPopUp selectedItem] representedObject] coId];
    [item setTemplateId:selectedTemplateId];

    switch(item.state)
    {
        case @"active":
            [item setState:@"changed"];
            break;
        case @"changed":
            [item setState:@"changed"];
            break;
        case @"new":
            [item setState:@"new"];
            break;
        default:
            [item setState:@"new"];
    }
    [super saveModel:sender];
}

@end
