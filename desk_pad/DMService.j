@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>
@import <CouchResource/COResource.j>

var  servicePropertyNamesArray = [[CPMutableArray alloc] init];

@implementation DMServicePackageProperty : CPObject
{
    CPString name     @accessors();
    CPString property @accessors();
    CPString value    @accessors();
}

- (CPString)nameIdentifierString
{
    return @"name";
}
@end


@implementation DMPropertyCellView : CPTableCellView
{
    @outlet CPPopUpButton namePUB;
    @outlet CPPopUpButton propertyPUB;
    @outlet CPTextField valueText;
}

+ (CPMutableArray)namesArray
{
    return servicePropertyNamesArray;
}

- (void)awakeFromCib
{
    [valueText bind:@"value"
               toObject:self
            withKeyPath:@"objectValue.value"
                options:nil];
    [namePUB bind:@"selectedValue"
               toObject:self
            withKeyPath:@"objectValue.name"
                options:nil];
    [propertyPUB bind:@"selectedValue"
               toObject:self
            withKeyPath:@"objectValue.property"
                options:nil];
}

- (void)setObjectValue:(id)aValue
{
    [[namePUB menu] removeAllItems];
    [servicePropertyNamesArray enumerateObjectsUsingBlock:function(item) {
        [namePUB addItem:[item copy]];
    }];

    [[propertyPUB menu] removeAllItems];
    var representedObject = [[namePUB itemAtIndex:0] representedObject];
    [representedObject enumerateObjectsUsingBlock:function(item) {
        var menuItem = [[CPMenuItem alloc] init];
        [menuItem setTitle:item.name];
        [propertyPUB addItem:menuItem];
    }];
    [super setObjectValue:aValue];
}
@end

@implementation DMIncludedServiceItem : CPObject
{
    CPString itemid   @accessors();
}

- (CPString)nameIdentifierString
{
    return @"itemid";
}
@end

@implementation DMIncludedServiceItemCellView : CPTableCellView
{
    @outlet CPTextField itemidField;
    @outlet CPTextField itemidFieldPopOver;
    CPObject test;
}

- (void)awakeFromCib
{
    [itemidField bind:@"value"
               toObject:self
            withKeyPath:@"objectValue.itemid"
                options:nil];
}

- (void)setObjectValue:(id)aValue
{
    // aValue.itemid = @"6";
    [super setObjectValue:aValue];
}
@end

@implementation DMServiceDefinition : COResource
{
    /* default ivars for couchdb */
    CPString coId @accessors();
    CPString coRev  @accessors();

    /* custom ivars */
    CPString serviceType  @accessors();
    CPArray packages @accessors();
    CPDictionary addons @accessors();
    CPDictionary properties @accessors();
}

+ (id)couchId:(id)aItem
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (CPString)nameIdentifierString
{
    return @"serviceType";
}
@end
