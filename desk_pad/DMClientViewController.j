@import <AppKit/CPPopover.j>
@import <AppKit/CPArrayController.j>
@import <CouchResource/COArrayController.j>
@import <CouchResource/COViewController.j>
@import "DMService.j"

@implementation DMClientViewController : COViewController
{
    CPMutableArray       serviceItems @accessors();
    @outlet              CPButton addServiceButton;
    @outlet              CPTableView servicesTV;
    @outlet              CPArrayController servicesAC;
    @outlet              CPTextField startDateInput;
    @outlet              CPTextField endDateInput;
    @outlet              CPTextField priceInput;
    @outlet              CPTextField discountTextInput;
    @outlet              CPView viewService;
    @outlet              CPPopover popoverService;

    CPMutableArray       serviceDefinitions @accessors();
    @outlet              CPPopUpButton serviceDefinitionPopUp;
    @outlet              CPPopUpButton serviceDefinitionPackagePopUp;
    @outlet              CPButton newServiceButton;
    @outlet              CPButton addPropertyButton;
    @outlet              CPButton removePropertyButton;

    CPMutableArray       packagePropertiesItems @accessors();
    @outlet              CPArrayController packagePropertiesAC;
    @outlet              CPTableView packageProperties;

    CPMutableArray       includedServiceItems @accessors();
    @outlet              CPArrayController includedServiceAC;
    @outlet              CPButton addIncludedButton;
    @outlet              CPView viewIncluded;
    @outlet              CPPopover popoverIncluded;
    @outlet              CPPopUpButton includedTypePUB;
    @outlet              CPTextField itemidInputIncluded;
    @outlet              CPPopUpButton itemTypeInputIncluded;
    @outlet              CPTextField startDateInputIncluded;
    @outlet              CPTextField endDateInputIncluded;

    CPMutableArray       addonServiceItems @accessors();
    @outlet              CPArrayController addonServiceAC;
    @outlet              CPButton addAddonButton;
    @outlet              CPView viewAddon;
    @outlet              CPPopover popoverAddon;
    @outlet              CPPopUpButton addonTypePUB;
    @outlet              CPTextField itemidInputAddon;
    @outlet              CPPopUpButton itemTypeInputAddon;
    @outlet              CPTextField startDateInputAddon;
    @outlet              CPTextField endDateInputAddon;
    @outlet              CPTextField priceInputAddon;
    @outlet              CPTextField discountTextInputAddon;

    CPMutableDictionary  itemLookup @accessors();
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
        //serviceItems addObject:[[DMService alloc] init]];
    }
    return self;
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


- (void)viewDidLoad
{
    [super viewDidLoad];

    [newServiceButton setAction:@selector(showNewService:)];
    [newServiceButton setTarget:self];
    [addServiceButton setAction:@selector(hideAddService:)];
    [addServiceButton setTarget:self];

    [popoverIncluded setAnimates:NO];
    [popoverAddon setAnimates:NO];

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
    var itemIncluded = [DMIncludedServiceItemCellView itemIncluded];
    itemIncluded.itemidInput = itemidInputIncluded;
    itemIncluded.itemType = itemTypeInputIncluded;
    itemIncluded.startDate = startDateInputIncluded;
    itemIncluded.endDate = endDateInputIncluded;
    itemIncluded.viewIncluded = viewIncluded;
    itemIncluded.popoverIncluded = popoverIncluded;

    var itemAddon = [DMAddonServiceItemCellView itemAddon];
    itemAddon.itemidInput = itemidInputAddon;
    itemAddon.itemType = itemTypeInputAddon;
    itemAddon.startDate = startDateInputAddon;
    itemAddon.endDate = endDateInputAddon;
    itemAddon.price = priceInputAddon;
    itemAddon.discountText = discountTextInputAddon;
    itemAddon.viewAddon = viewAddon;
    itemAddon.popoverAddon = popoverAddon;
    itemAddon.view = viewService;

    var serviceItem = [DMServiceItemCellView serviceItem];
    serviceItem.view = viewService;
    serviceItem.popoverService = popoverService;
    serviceItem.serviceType = serviceDefinitionPopUp;
    serviceItem.packageType = serviceDefinitionPackagePopUp;
    serviceItem.startDate = startDateInput;
    serviceItem.endDate = endDateInput;
    serviceItem.price = priceInput;
    serviceItem.discountText = discountTextInput;
    serviceItem.packagePropertiesAC = packagePropertiesAC;
    serviceItem.includedServiceAC = includedServiceAC;
    serviceItem.addonServiceAC = addonServiceAC;
    serviceItem.clientViewController = self;
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
    }
    if (currentDefinitionPackages.hasOwnProperty("allowed_addons"))
    {
        [self buildMenu:addonTypePUB items:currentDefinitionPackages.allowed_addons];
    }
}

- (void)showNewService:(id)sender
{
    [popoverService setAnimates:NO];
    [[popoverService contentViewController] setView:viewService];
    if (![popoverService isShown])
    {
        [popoverService showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [self updateServiceDefinition];
        [self updateServicePackageDefinition];
        [self resetServiceView];
    } else {
        [popoverService close];
    }
}

- (void)resetServiceView
{
    [[packagePropertiesAC contentArray] removeAllObjects];
    [[includedServiceAC contentArray] removeAllObjects];
    [[addonServiceAC contentArray] removeAllObjects];
    [startDateInput setStringValue:@""];
    [endDateInput setStringValue:@""];
    [priceInput setStringValue:@""];
    [discountTextInput setStringValue:@""];
    [serviceDefinitionPopUp selectItemAtIndex:0];
    [serviceDefinitionPackagePopUp selectItemAtIndex:0];
}

- (void)hideAddService:(id)sender
{
    var newServiceItem = [[DMServiceItem alloc] init];
    newServiceItem.serviceType = [serviceDefinitionPopUp titleOfSelectedItem];
    newServiceItem.startDate = [startDateInput stringValue];
    newServiceItem.endDate = [endDateInput stringValue];
    newServiceItem.price = [priceInput stringValue];
    newServiceItem.discountText = [discountTextInput stringValue];
    newServiceItem.includedServiceItems = [[CPMutableArray alloc] initWithArray:[includedServiceAC contentArray] copyItems:YES];
    newServiceItem.addonServiceItems = addonServiceItems;

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
    if (![itemLookup valueForKey:[item coId]])
    {
        //[clientsForProjectsPopUp addItemWithTitle:[client name]];
        [itemLookup setObject:item forKey:[item coId]];
    }
}
@end
