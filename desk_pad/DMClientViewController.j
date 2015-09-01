@import <AppKit/CPPopover.j>
@import <CouchResource/COArrayController.j>
@import <CouchResource/COViewController.j>


@implementation DMClientViewController : COViewController
{
    @outlet              CPButton addServiceButton;
    @outlet              CPView viewService;
    @outlet              CPPopover popoverService;
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
    }
    return self;
}


- (void)viewDidLoad
{
    [super viewDidLoad];

    [addServiceButton setAction:@selector(addService:)];
    [addServiceButton setTarget:self];
}

- (void)addService:(id)sender
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

- (void)popoverDidShow:(CPPopover)aPopover
{
    [CPApp runModalForWindow:[[[aPopover contentViewController] view] window]];
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
