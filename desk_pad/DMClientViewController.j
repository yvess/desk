@import <AppKit/CPPopover.j>
@import <AppKit/CPArrayController.j>
@import <CouchResource/COArrayController.j>
@import <CouchResource/COViewController.j>
@import "DMService.j"

@implementation DMClientViewController : COViewController
{
    @outlet              CPButton addServiceButton;
    @outlet              CPButton addIncludedButton;
    @outlet              CPButton addAddonButton;
    @outlet              CPButton addPropertyButton;
    @outlet              CPButton removePropertyButton;
    @outlet              CPView viewService;
    @outlet              CPView viewIncluded;
    @outlet              CPView viewAddon;
    @outlet              CPPopover popoverService;
    @outlet              CPPopover popoverIncluded;
    @outlet              CPPopover popoverAddon;
    @outlet              CPTableView packageProperties;
    @outlet              COArrayController packagePropertiesController;
    @outlet              CPPopUpButton serviceDefinitionPopUp;
    @outlet              CPPopUpButton serviceDefinitionPackagePopUp;
    @outlet              CPPopUpButton includedTypePUB;
    @outlet              CPPopUpButton addonTypePUB;
    @outlet              CPTextField itemidIncludedFieldInput;
    CPMutableArray       packagePropertiesItems @accessors();
    CPMutableArray       includedServiceItems @accessors();
    CPMutableArray       addonServiceItems @accessors();
    CPMutableArray       serviceDefinitions @accessors();
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

    [addServiceButton setAction:@selector(showService:)];
    [addServiceButton setTarget:self];

    [addAddonButton setAction:@selector(showAddon:)];
    [addAddonButton setTarget:self];

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
    var itemidIncluded = [DMIncludedServiceItemCellView itemIncluded];
    itemidIncluded.itemidInput = itemidIncludedFieldInput;
    itemidIncluded.viewIncluded = viewIncluded;
    itemidIncluded.popoverIncluded = popoverIncluded;
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

- (void)showService:(id)sender
{
    [popoverService setAnimates:NO];
    [[popoverService contentViewController] setView:viewService];
    if (![popoverService isShown])
    {
        [popoverService showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [self updateServiceDefinition];
        [self updateServicePackageDefinition];
    } else {
        [popoverService close];
    }

}

- (void)showAddon:(id)sender
{
    [[popoverAddon contentViewController] setView:viewAddon];
    if (![popoverAddon isShown])
    {
        [popoverIncluded close];
        [popoverAddon showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
    } else {
        [popoverAddon close];
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
