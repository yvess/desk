@import <AppKit/CPViewController.j>
@import <AppKit/CPEvent.j>
@import <AppKit/CPView.j>
@import <CouchResource/COViewController.j>
@import "DMInspectorItem.j"

@implementation DMInspectorViewController : COViewController
{
    // @outlet     CPView view;
    // @outlet     COArrayController arrayController;
    // @outlet     CPTableView itemsTable;
    // CPArray     items;
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
      modelClass: (CPObject) aModelClass
      growlCenter: (TNGrowlCenter) aGrowlCenter
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass growlCenter:aGrowlCenter];
    if (self)
    {
    }
    return self;
}

- (void)reloadItems
{
    [self setItems:[modelClass allWithParams:{} withPath:@"/inspector_items"]];
}


- (void)viewDidLoad
{
    [super viewDidLoad];
    //[arrayController addObserver:self forKeyPath:@"selection.inspectorItems" options:nil context:@"inspectorItems"];
}

@end
