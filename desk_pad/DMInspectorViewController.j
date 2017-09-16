@import <AppKit/CPViewController.j>
@import <AppKit/CPEvent.j>
@import <AppKit/CPView.j>
@import <CouchResource/COViewController.j>
@import "DMInspectorItem.j"

@implementation DMInspectorViewController : COViewController
{
    @outlet              CPView view;
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
      modelClass: (CPObject) aModelClass
      growlCenter: (TNGrowlCenter) aGrowlCenter
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass growlCenter:aGrowlCenter];
    if (self)
    {
        items = [modelClass allWithParams:@{} withPath:@"/domains_by_name"];
    }
    return self;
}

- (void)reloadItems
{
    [self setItems:[modelClass allWithParams:@{} withPath:@"/domains_by_name"]];
}


- (void)viewDidLoad
{
    [super viewDidLoad];
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

@end
