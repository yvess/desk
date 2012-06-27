@import <CouchResource/COArrayController.j>
@import <CouchResource/COViewController.j>


@implementation DMClientViewController : COViewController
{
    CPMutableDictionary   itemLookup @accessors();
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

- (void)saveModel:(id)sender
{
    [super saveModel:sender];
    var item = [[arrayController selectedObjects] lastObject];
    if (![itemLookup valueForKey:[item coId]])
    {
        //[clientsForProjectsPopUp addItemWithTitle:[client name]];
        [itemLookup setObject:item forKey:[item coId]];
    }
    console.log("itemLookup", self, itemLookup);
}

/*- (void)viewDidLoad
{
    [super viewDidLoad];
    [items enumerateObjectsUsingBlock:function(item) {
        //[clientsForProjectsPopUp addItemWithTitle:[item name]];
        [itemLookup setObject:item forKey:[item coId]];
        console.log("item", item);
    }];
    console.log("items", items);
    console.log("viewDidLoad", itemLookup);
}*/
/*{
    IBOutlet              DMArrayController clientArrayController;
    IBOutlet              CPTableView clientsTable;
    IBOutlet              CPButton saveClientButton;

    CPMutableArray        clients;
    CPMutableDictionary   itemLookup;
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil];
    if (self)
    {
        var clients = [DMClient all];
        [clients class];
    }
    return self;
}

- (void)saveClient:(id)sender
{
    var client = [[clientArrayController selectedObjects] lastObject];
    if (![client coId])
    {
        [client setCoId:[[client class] couchId:client]];
    }
    [client save];
    if (![itemLookup valueForKey:[client coId]])
    {
        //[clientsForProjectsPopUp addItemWithTitle:[client name]];
        [itemLookup setObject:client forKey:[client coId]];
    }
}

- (void)viewDidLoad
{
    [saveClientButton setTarget:self];
    [saveClientButton setAction:@selector(saveClient:)];
}*/
@end
