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
    CPMutableArray       packagePropertiesItems @accessors();
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
        serviceDefinitions = [DMServiceDefinition all];
    }
    return self;
}

- (void)popUpSelectionChanged:(CPNotification)notification
{
    [self updatePackagePopup];
}

- (void)viewDidLoad
{
    [super viewDidLoad];

    [addServiceButton setAction:@selector(showService:)];
    [addServiceButton setTarget:self];

    [addIncludedButton setAction:@selector(showIncluded:)];
    [addIncludedButton setTarget:self];

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
        selector:@selector(popUpSelectionChanged:)
            name:CPMenuDidChangeItemNotification
          object:[serviceDefinitionPopUp menu]
    ];
}

- (void)updatePackagePopup
{
    [[serviceDefinitionPackagePopUp menu] removeAllItems];
    var currentServiceDefinition = [[serviceDefinitionPopUp selectedItem] representedObject];
    [currentServiceDefinition.packages.items enumerateObjectsUsingBlock:function(item) {
        var menuItem = [[CPMenuItem alloc] init];
        [menuItem setTitle:item.name];
        [menuItem setRepresentedObject:item];
        [serviceDefinitionPackagePopUp addItem:menuItem];
        serviceDefinitionPackagePopUp
    }];
}

- (void)showService:(id)sender
{
    [popoverService setAnimates:NO];
    [[popoverService contentViewController] setView:viewService];
    if (![popoverService isShown])
    {
        [popoverService showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [self updatePackagePopup];
    } else {
        [popoverService close];
    }

}

- (void)showIncluded:(id)sender
{
    [[popoverIncluded contentViewController] setView:viewIncluded];
    if (![popoverIncluded isShown])
    {
        [popoverAddon close];
        [popoverIncluded showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
    } else {
        [popoverIncluded close];
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
