@import <CouchResource/COArrayController.j>
@import <CouchResource/COViewController.j>

@implementation DMWorkTimeViewController : COViewController
{
}

- (id)initWithCibName:(CPString) aCibNameOrNil
      bundle: (CPBundle) aCibBundleOrNil
      modelClass: (CPObject) aModelClass
{
    self = [super initWithCibName:aCibNameOrNil bundle:aCibBundleOrNil modelClass:aModelClass];
    if (self)
    {
    }
    return self;
}

- (void)viewDidLoad
{
    /*[workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.date" options:nil context:@"date"];
    [workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.time" options:nil context:@"time"];
    [workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.duration" options:nil context:@"duration"];
    [workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.projectId" options:nil context:@"projectId"];
    [workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.billable" options:nil context:@"billable"];
    [workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.category" options:nil context:@"category"];
    [workTimeArrayController addObserver:self forKeyPath:@"arrangedObjects.comment" options:nil context:@"comment"];*/

    /*

    // billable popup
    var billableColumn = [workTimesTable tableColumnWithIdentifier:@"billable"],
        billablePopUp = [[CPPopUpButton alloc] initWithFrame:CGRectMake([billableColumn width], 12)];
    [WTBillableArray enumerateObjectsUsingBlock:function(item) {
        [billablePopUp addItemWithTitle:item];
    }];
    [billableColumn setDataView:billablePopUp];

    // category popup
    var categoryColumn = [workTimesTable tableColumnWithIdentifier:@"category"],
        categoryPopUp = [[CPPopUpButton alloc] initWithFrame:CGRectMake([categoryColumn width], 12)];
    [WTCategoryArray enumerateObjectsUsingBlock:function(item) {
        [categoryPopUp addItemWithTitle:item];
    }];
    [categoryColumn setDataView:categoryPopUp];

    // projects popup
    var projectColumn = [workTimesTable tableColumnWithIdentifier:@"projectId"],
        projectPopUp = [[CPPopUpButton alloc] initWithFrame:CGRectMake([projectColumn width], 12)];
    [projects enumerateObjectsUsingBlock:function(item) {
        [projectPopUp addItemWithTitle:[item name]];
    }];
    [projectColumn setDataView:projectPopUp];

    [workTimesTable reloadData];*/

}

- (void)observeValueForKeyPath:(CPString)aKeyPath
        ofObject:(id)anObject
        change:(CPDictionary)aChange
        context:(id)aContext
{
    var item = [[anObject arrangedObjects] objectAtIndex:[anObject selectionIndex]],
        new_value = [aChange valueForKey:@"CPKeyValueChangeNewKey"],
        old_value = [aChange valueForKey:@"CPKeyValueChangeOldKey"];

    /* WorkTime */
    /*if ([item class] == [DMWorkTime class])
    {
        if (![new_value isEqual:old_value])
        {
            if (aContext == "date" || aContext == "time")
            {
                var aNewWorkTime = [[DMWorkTime alloc] init];
                [aNewWorkTime setAttributes:[item attributes]];
                [aNewWorkTime setIdentifier:null];
                [aNewWorkTime setCoId:[[aNewWorkTime class] couchId:aNewWorkTime]];
                [aNewWorkTime save]; // TODO check if it really got saved
                [item destroy];
            } else {
                [item save];
            }
        }
    }*/
}
@end
