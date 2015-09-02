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
    CPMutableArray       packagePropertiesItems @accessors();
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
    }
    return self;
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
    console.log(packagePropertiesItems);
}

- (void)showService:(id)sender
{
    [popoverService setAnimates:NO];
    [[popoverService contentViewController] setView:viewService];
    if (![popoverService isShown])
    {
        [popoverService showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
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
