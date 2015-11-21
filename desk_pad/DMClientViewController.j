@import <AppKit/CPPopover.j>
@import <AppKit/CPArrayController.j>
@import <CouchResource/COViewController.j>
@import "DMService.j"
@import "DMClient.j"
@import "DMDomain.j"

@implementation DMClientViewController : COViewController
{
    CPMutableArray       serviceItems @accessors;
    @outlet              CPButton addServiceButton;
    @outlet              CPTableView servicesTV;
    @outlet              CPArrayController servicesAC;
    @outlet              CPTextField startDateInput;
    @outlet              CPTextField endDateInput;
    @outlet              CPTextField priceInput;
    @outlet              CPTextField packageTitleInput;
    @outlet              CPTextField discountTextInput;
    @outlet              CPView viewService;
    @outlet              CPPopover popoverService;

    CPMutableArray       serviceDefinitions @accessors;
    @outlet              CPPopUpButton serviceDefinitionPopUp;
    @outlet              CPPopUpButton serviceDefinitionPackagePopUp;
    @outlet              CPButton newServiceButton;
    @outlet              CPButton addPropertyButton;
    @outlet              CPButton removePropertyButton;

    CPMutableArray       packagePropertiesItems @accessors;
    @outlet              CPArrayController packagePropertiesAC;
    @outlet              CPTableView packageProperties;

    CPMutableArray       includedServiceItems @accessors;
    @outlet              CPArrayController includedServiceAC;
    @outlet              CPButton addIncludedButton;
    @outlet              CPButton removeIncludedButton;
    @outlet              CPView viewIncluded;
    @outlet              CPPopover popoverIncluded;
    @outlet              CPPopUpButton includedTypePUB;
    @outlet              CPTextField itemidInputIncluded;
    @outlet              CPPopUpButton itemTypeInputIncluded;
    @outlet              CPTextField startDateInputIncluded;
    @outlet              CPTextField endDateInputIncluded;
    @outlet              CPTextField notesInputIncluded;

    CPMutableArray       addonServiceItems @accessors;
    @outlet              CPArrayController addonServiceAC;
    @outlet              CPButton addAddonButton;
    @outlet              CPButton removeAddonButton;
    @outlet              CPView viewAddon;
    @outlet              CPPopover popoverAddon;
    @outlet              CPPopUpButton addonTypePUB;
    @outlet              CPTextField itemidInputAddon;
    @outlet              CPPopUpButton itemTypeInputAddon;
    @outlet              CPTextField startDateInputAddon;
    @outlet              CPTextField endDateInputAddon;
    @outlet              CPTextField priceInputAddon;
    @outlet              CPTextField discountTextInputAddon;
    @outlet              CPTextField notesInputAddon;

    CPMutableDictionary  itemLookup @accessors;

    CPMutableArray       domainItems @accessors;
    @outlet              CPTableView domainsTV;
    @outlet              CPArrayController domainsAC;
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
      modelClass: (CPObject) aModelClass
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass];
    if (self)
    {
        itemLookup = [self createLookup];
        packagePropertiesItems = [[CPMutableArray alloc] init];
        includedServiceItems = [[CPMutableArray alloc] init];
        addonServiceItems = [[CPMutableArray alloc] init];
        serviceDefinitions = [DMServiceDefinition all];
        serviceItems = [[CPMutableArray alloc] init];
        domainItems = [[CPMutableArray alloc] init];
    }
    return self;
}

- (void)loadServicesByClient:(DMClient)aClient
{
    [self resetServiceView];
    var clientkey = '"' + aClient.coId + '"',
        serviceItemsCouch = [
        DMService allWithParams:@{ @"startkey": clientkey, @"endkey": clientkey }
                  withPath:@"/services_by_client"];
    [serviceItems removeAllObjects];
    [serviceItems addObjectsFromArray:serviceItemsCouch];
    [servicesAC setContent:serviceItems];
}

- (void)loadDomainsByClient:(DMClient)aClient
{
    var clientkey = '"' + aClient.coId + '"',
        domainItemsCouch = [
        DMDomain allWithParams:@{ @"startkey": clientkey, @"endkey": clientkey }
                 withPath:@"/domains_by_client"];
    [domainItems removeAllObjects];
    [domainItems addObjectsFromArray:domainItemsCouch];
    [domainsAC setContent:domainItems];
}

- (void)servicePopUpSelectionChanged:(CPNotification)notification
{
    [self updateServiceDefinition];
    [self updateServicePackageDefinition];
}

- (void)servicePackagePopUpSelectionChanged:(CPNotification)notification
{
    [self updateServicePackageDefinition];
}

- (void)servicePropertyNameSelectionChanged:(CPNotification)notification
{
    //console.log("servicePropertyNameSelectionChanged", notification);
}

- (void)observeValueForKeyPath:(CPString) aKeyPath
        ofObject:(id) anObject
        change:(CPDictionary) aChange
        context:(id) aContext
{
    if (aContext == @"client")
    {
        var selectedClient = [[anObject selectedObjects] lastObject];
        [self loadServicesByClient:selectedClient];
        [self loadDomainsByClient:selectedClient];
    }
}

- (void)awakeFromCib
{
    [window.popovers addObject:popoverService];
    [window.popovers addObject:popoverIncluded];
    [window.popovers addObject:popoverAddon];
    [window.popovers addObject:popoverService];
}

- (void)viewDidLoad
{
    [super viewDidLoad];

    [newServiceButton setAction:@selector(showNewService:)];
    [newServiceButton setTarget:self];
    [addServiceButton setAction:@selector(hideAddService:)];
    [addServiceButton setTarget:self];

    [popoverIncluded setAnimates:NO];
    [popoverAddon setAnimates:NO];
    [popoverService setAnimates:NO];
    [[popoverService contentViewController] setView:viewService];

    [serviceDefinitions enumerateObjectsUsingBlock:function(item) {
        var menuItem = [[CPMenuItem alloc] init];
        [menuItem setTitle:item.serviceType];
        [menuItem setRepresentedObject:item];
        [serviceDefinitionPopUp addItem:menuItem];
    }];

    [[CPNotificationCenter defaultCenter] addObserver:self
        selector:@selector(servicePopUpSelectionChanged:)
            name:CPMenuDidChangeItemNotification
          object:[serviceDefinitionPopUp menu]
    ];
    [[CPNotificationCenter defaultCenter] addObserver:self
        selector:@selector(servicePackagePopUpSelectionChanged:)
            name:CPMenuDidChangeItemNotification
          object:[serviceDefinitionPackagePopUp menu]
    ];
    [[CPNotificationCenter defaultCenter] addObserver:self
        selector:@selector(servicePropertyNameSelectionChanged:)
            name:CPMenuDidChangeItemNotification
          object:nil
    ];

    [arrayController addObserver:self forKeyPath:@"selection.client" options:nil context:@"client"];

    var itemIncluded = [DMIncludedServiceItemCellView itemIncluded];
    itemIncluded.itemidInput = itemidInputIncluded;
    itemIncluded.itemType = itemTypeInputIncluded;
    itemIncluded.startDate = startDateInputIncluded;
    itemIncluded.endDate = endDateInputIncluded;
    itemIncluded.notes = notesInputIncluded;
    itemIncluded.viewIncluded = viewIncluded;
    itemIncluded.popoverIncluded = popoverIncluded;

    var itemAddon = [DMAddonServiceItemCellView itemAddon];
    itemAddon.itemidInput = itemidInputAddon;
    itemAddon.itemType = itemTypeInputAddon;
    itemAddon.startDate = startDateInputAddon;
    itemAddon.endDate = endDateInputAddon;
    itemAddon.price = priceInputAddon;
    itemAddon.discountText = discountTextInputAddon;
    itemAddon.notes = notesInputAddon;
    itemAddon.viewAddon = viewAddon;
    itemAddon.popoverAddon = popoverAddon;
    itemAddon.view = viewService;

    var serviceItem = [DMServiceCellView serviceItem];
    serviceItem.view = viewService;
    serviceItem.servicesAC = servicesAC;
    serviceItem.popoverService = popoverService;
    serviceItem.addServiceButton = addServiceButton;
    serviceItem.serviceType = serviceDefinitionPopUp;
    serviceItem.packageType = serviceDefinitionPackagePopUp;
    serviceItem.startDate = startDateInput;
    serviceItem.endDate = endDateInput;
    serviceItem.price = priceInput;
    serviceItem.packageTitle = packageTitleInput;
    serviceItem.discountText = discountTextInput;
    serviceItem.packagePropertiesAC = packagePropertiesAC;
    serviceItem.includedServiceAC = includedServiceAC;
    serviceItem.addonServiceAC = addonServiceAC;
    serviceItem.clientViewController = self;

    [self updateServiceDefinition];
    [self updateServicePackageDefinition];
    if ([items count] > 0) // no clients
    {
        [self loadServicesByClient:[items objectAtIndex:0]]; // first client
        [self loadDomainsByClient:[items objectAtIndex:0]];
    }
}

- (void)buildMenu:(id)aMenuHolder items:(id)someItems
{
    var filler = function(key, value) {
        var menuItem = [[CPMenuItem alloc] init];
        [menuItem setTitle:key];
        if (value != null)
        {
            [menuItem setRepresentedObject:value];
        }
        if ([aMenuHolder respondsToSelector:@selector(addItem:)])
        {
            [aMenuHolder addItem:menuItem];
        } else if ([aMenuHolder respondsToSelector:@selector(addObject:)]) {
            [aMenuHolder addObject:menuItem];
        }
    };
    try // array case
    {
        if ([someItems className] == @"_CPJavaScriptArray")
        {
            someItems.forEach(function(item) {
                filler(item, null);
            });
        }
    } catch (err) { // object / hashmap case
        for (key in someItems)
        {
            filler(key, someItems[key]);
        }
    }
}

- (void)updateServiceDefinition
{
    [[serviceDefinitionPackagePopUp menu] removeAllItems];
    var currentServiceDefinition = [[serviceDefinitionPopUp selectedItem] representedObject];
    [self buildMenu:serviceDefinitionPackagePopUp items:currentServiceDefinition.packages];
    if (currentServiceDefinition.hasOwnProperty("properties"))
    {
        [[DMPropertyCellView namesArray] removeAllObjects];
        [self buildMenu:[DMPropertyCellView namesArray] items:currentServiceDefinition.properties];
        [addPropertyButton setEnabled:YES];
        [removePropertyButton setEnabled:YES];
    }
    else {
        [[DMPropertyCellView namesArray] removeAllObjects];
        [addPropertyButton setEnabled:NO];
        [removePropertyButton setEnabled:NO];
    }
}

- (void)updateServicePackageDefinition
{
    [[includedTypePUB menu] removeAllItems];
    [[addonTypePUB menu] removeAllItems];
    var currentDefinitionPackages = [[serviceDefinitionPackagePopUp selectedItem] representedObject];
    if (currentDefinitionPackages.hasOwnProperty("included"))
    {
        [self buildMenu:includedTypePUB items:currentDefinitionPackages.included];
        [addIncludedButton setEnabled:YES];
        [removeIncludedButton setEnabled:YES];
    } else {
        [addIncludedButton setEnabled:NO];
        [removeIncludedButton setEnabled:NO];
    }
    if (currentDefinitionPackages.hasOwnProperty("allowed_addons"))
    {
        [self buildMenu:addonTypePUB items:currentDefinitionPackages.allowed_addons];
        [addAddonButton setEnabled:YES];
        [removeAddonButton setEnabled:YES];
    } else {
        [addAddonButton setEnabled:NO];
        [removeAddonButton setEnabled:NO];
    }
}

- (void)showNewService:(id)sender
{
    [addServiceButton setHidden:NO];
    [viewService setNeedsDisplay:YES];

    if (![popoverService isShown])
    {
        [popoverService showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [self updateServiceDefinition];
        [self resetServiceView];
    } else {
        [popoverService close];
    }
}

- (void)resetServiceView
{
    [self updateServiceDefinition];
    [serviceDefinitionPopUp selectItemAtIndex:0];
    [serviceDefinitionPackagePopUp selectItemAtIndex:0];

    [packagePropertiesAC setContent:[[CPMutableArray alloc] init]];
    [includedServiceAC setContent:[[CPMutableArray alloc] init]];
    [addonServiceAC setContent:[[CPMutableArray alloc] init]];
    [startDateInput setStringValue:@""];
    [endDateInput setStringValue:@""];
    [priceInput setStringValue:@""];
    [packageTitleInput setStringValue:@""];
    [discountTextInput setStringValue:@""];
}

- (void)hideAddService:(id)sender
{
    var newServiceItem = [[DMService alloc] init];
    newServiceItem.clientId = [[self lastSelectedObject] identifier];
    newServiceItem.serviceType = [serviceDefinitionPopUp titleOfSelectedItem];
    newServiceItem.packageType = [serviceDefinitionPackagePopUp titleOfSelectedItem];
    newServiceItem.startDate = [startDateInput stringValue];
    newServiceItem.endDate = [endDateInput stringValue];
    newServiceItem.price = [priceInput stringValue];
    newServiceItem.packageTitle = [packageTitleInput stringValue];
    newServiceItem.discountText = [discountTextInput stringValue];
    newServiceItem.packagePropertiesItems = [[CPMutableArray alloc] initWithArray:[packagePropertiesAC contentArray] copyItems:YES];
    newServiceItem.includedServiceItems = [[CPMutableArray alloc] initWithArray:[includedServiceAC contentArray] copyItems:YES];
    newServiceItem.addonServiceItems = [[CPMutableArray alloc] initWithArray:[addonServiceAC contentArray] copyItems:YES];

    [servicesAC addObject:newServiceItem];
    if ([popoverService isShown])
    {
        [popoverService close];
    }
}

- (void)saveModel:(id)sender
{
    [super saveModel:sender];
    var item = [[arrayController selectedObjects] lastObject];
    [serviceItems enumerateObjectsUsingBlock:function(item) {
        var serviceSaved = [item save];
    }];
    if (![itemLookup valueForKey:[item coId]])
    {
        //[clientsForProjectsPopUp addItemWithTitle:[client name]];
        [itemLookup setObject:item forKey:[item coId]];
    }
}
@end
