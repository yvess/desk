@import <CouchResource/COArrayController.j>
@import <CouchResource/COViewController.j>

@implementation DMProjectViewController : COViewController
{
    IBOutlet              CPPopUpButton clientsForProjectsPopUp;
    CPMutableDictionary   itemLookup;
    CPMutableArray        clients;
    CPMutableDictionary   clientLookup;
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
      modelClass: (CPObject) aModelClass
      clients: (CPMutableArray) aClientArray
      clientLookup: (CPMutableDictionary) aClientLookup
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass];
    if (self)
    {
        itemLookup = [self createLookup];
        clients = aClientArray;
        clientLookup = aClientLookup;
    }
    return self;
}

- (void)observeValueForKeyPath:(CPString)aKeyPath
        ofObject:(id)anObject
        change:(CPDictionary)aChange
        context:(id)aContext
{
    var item = [[anObject arrangedObjects] objectAtIndex:[anObject selectionIndex]],
        new_value = [aChange valueForKey:@"CPKeyValueChangeNewKey"],
        old_value = [aChange valueForKey:@"CPKeyValueChangeOldKey"];

    if ([item class] == [self modelClass])
    {
        var clientIndex = [clients indexOfObject:[clientLookup objectForKey:[item clientId]]];
        [clientsForProjectsPopUp selectItemAtIndex:clientIndex];
    }
}

- (void)saveModel:(id)sender
{
    var item = [self lastSelectedObject],
        selectedClientId = [[clients objectAtIndex:[clientsForProjectsPopUp indexOfSelectedItem]] coId];
    [item setClientId:selectedClientId];
    [super saveModel:sender];
}

- (void)viewDidLoad
{
    [super viewDidLoad];
    [clients enumerateObjectsUsingBlock:function(item) {
        [clientsForProjectsPopUp addItemWithTitle:[item name]];
    }];
    [arrayController addObserver:self forKeyPath:@"selection.name" options:nil context:@"name"];
    //[arrayController addObserver:self forKeyPath:@"selection.client" options:nil context:@"clientId"];
}

/*- (void)saveProject:(id)sender
{
    if ([[projectPopUp itemTitles] indexOfObject:[aProject name]] < 0)
    {
        [projectPopUp addItemWithTitle:[aProject name]];
    }
    if ([WTProjectsArray indexOfObject:[aProject coId]] < 0)
    {
        [WTProjectsArray addObject:[aProject coId]];
    }
    var projectColumn = [workTimesTable tableColumnWithIdentifier:@"projectId"],
        projectPopUp = [[CPPopUpButton alloc] initWithFrame:CGRectMake([projectColumn width], 12)];
    [projects enumerateObjectsUsingBlock:function(item) {
        [projectPopUp addItemWithTitle:[item name]];
    }];
    [projectColumn setDataView:projectPopUp];
    [workTimesTable reloadData];
}*/
@end
