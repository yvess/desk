@import <CouchResource/COResource.j>
@import "DMProject.j"

WTBillableArray = [[CPArray alloc] initWithObjects: @"in-offer",  @"not-in-offer", @"guarantee", @"goodwill", nil];
WTCategoryArray = [[CPArray alloc] initWithObjects: @"programming",  @"design", @"communication", nil];
WTProjectsArray = [[CPMutableArray alloc] init];

@implementation DMWorkTime : COResource
{
    CPString coId    @accessors();
    CPString coRev   @accessors();
    CPString date     @accessors();
    CPString time     @accessors();
    CPString duration @accessors();
    CPString comment  @accessors();
    int billable;
    int category;
    int projectId;
}

- (CPString)nameIdentifierString
{
    return @"name";
}

- (CPArray)billabeLookup
{
    return WTBillableArray;
}

- (CPString)billable
{
    var value = [[self billabeLookup] indexOfObject:billable];
    return value;
}

- (void)setBillable:(id)value
{
    if ([value isKindOfClass: [CPNumber class]])
    {
        billable = [[self billabeLookup] objectAtIndex:value];
    } else {
        billable = value;
    }
}

- (CPArray)categoryLookup
{
    return WTCategoryArray;
    // TODO set as constant
}

- (CPString)category
{
    var value = [[self categoryLookup] indexOfObject:category];
    return value;
}

- (void)setCategory:(id)value
{
    if ([value isKindOfClass: [CPNumber class]])
    {
        category = [[self categoryLookup] objectAtIndex:value];
    } else {
        category = value;
    }
}

- (CPArray)projectLookup
{
    if ([WTProjectsArray count] <= 0)
    {
        [[DMProject all] enumerateObjectsUsingBlock:function(item) {
            [WTProjectsArray addObject:[item coId]];
        }];
    }
    return WTProjectsArray;
    // TODO set as constant
}

- (CPString)projectId
{
    var value = [[self projectLookup] indexOfObject:projectId];
    return value;
}

- (void)setProjectId:(id)value
{
    if ([value isKindOfClass: [CPNumber class]])
    {
        projectId = [[self projectLookup] objectAtIndex:value];
    } else {
        projectId = value;
    }
}

+ (id)couchId:(id)aItem
{
    return [CPString stringWithFormat:@"%@;%@-%@", [aItem date], [aItem time], @"yserrano"];
}

- (id)initWithCurrentDate
{
    if (self)
    {
        var currentTimeDate = new Date(),
            month = currentTimeDate.getMonth()+1,
            day = currentTimeDate.getDate(),
            hours = currentTimeDate.getHours(),
            minutes = currentTimeDate.getMinutes(),
            remainer_min = minutes % 15,
            factor_min = Math.floor(minutes / 15);
        minutes = (remainer_min < 5) ? minutes = factor_min * 15 : minutes = (factor_min + 1) * 15;
        if (month < 10) month = "0" + month;
        if (day < 10) day = "0" + day;
        if (hours < 10) hours = "0" + hours;
        if (minutes < 10) minutes = "0" + minutes;
        [self setDate:[CPString stringWithFormat:@"%@-%@-%@",
            currentTimeDate.getFullYear(), month, day]];
        [self setTime:[CPString stringWithFormat:@"%@:%@",
            hours, minutes]];
        [self setCoId:[[self class] couchId:self]];
        [self setType:[[self class] underscoreName]];
        [self save];
    }
    return self;
}

@end
