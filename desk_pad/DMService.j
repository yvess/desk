@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>
@import <CouchResource/COResource.j>

var servicePropertyNamesArray = [[CPMutableArray alloc] init],
    itemIncluded = {},
    itemAddon = {};

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

// INCLUDED ITEM

@implementation DMIncludedServiceItem : CPObject
{
    CPString itemid @accessors();
    CPString itemType @accessors();
    CPString startDate @accessors();
    CPString endDate @accessors();
}

- (id)init
{
    self = [super init];
    if (self)
    {
        [self setItemid:@"NEW"];
        [self setItemType:@""];
        [self setStartDate:@""];
        [self setEndDate:@""];
    }
    return self;
}

- (CPString)nameIdentifierString
{
    return @"itemid";
}
@end

@implementation DMIncludedServiceItemCellView : CPTableCellView
{
    @outlet CPTextField itemidField;
    @outlet CPButton editButton;
}

+ (id)itemIncluded
{
    return itemIncluded;
}

- (void)awakeFromCib
{
    [itemidField bind:@"value"
       toObject:self
    withKeyPath:@"objectValue.itemid"
        options:nil];
    [editButton setAction:@selector(showEditIncluded:)];
    [editButton setTarget:self];
}

- (void)showEditIncluded:(id)sender
{
    [[itemIncluded.popoverIncluded contentViewController] setView:itemIncluded.viewIncluded];
    if ([itemIncluded.popoverIncluded isShown])
    {
        var ov = [self objectValue];
        ov.itemid = [itemIncluded.itemidInput stringValue];
        ov.itemType = [itemIncluded.itemType stringValue];
        ov.startDate = [itemIncluded.startDate stringValue];
        ov.endDate = [itemIncluded.endDate stringValue];
        [self setObjectValue:ov];
        [itemIncluded.popoverIncluded close];
    } else {
        [itemIncluded.popoverIncluded close];
        [itemIncluded.popoverIncluded showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [itemIncluded.itemidInput setStringValue:[[self objectValue] itemid]];
        [itemIncluded.itemType setStringValue:[[self objectValue] itemType]];
        [itemIncluded.startDate setStringValue:[[self objectValue] startDate]];
        [itemIncluded.endDate setStringValue:[[self objectValue] endDate]];
    }
}
@end

// ADDON ITEM

@implementation DMAddonServiceItem : CPObject
{
    CPString itemid   @accessors();
    CPString itemType @accessors();
    CPString startDate @accessors();
    CPString endDate @accessors();
    CPString price @accessors();
    CPString discountText @accessors();
}

- (id)init
{
    self = [super init];
    if (self)
    {
        [self setItemid:@"NEW"];
        [self setItemType:@""];
        [self setStartDate:@""];
        [self setEndDate:@""];
        [self setPrice:@""];
        [self setDiscountText:@""];
    }
    return self;
}

- (CPString)nameIdentifierString
{
    return @"itemid";
}
@end

@implementation DMAddonServiceItemCellView : CPTableCellView
{
    @outlet CPTextField itemidField;
    @outlet CPButton editButton;
}

+ (id)itemAddon
{
    return itemAddon;
}

- (void)awakeFromCib
{
    [itemidField bind:@"value"
       toObject:self
    withKeyPath:@"objectValue.itemid"
        options:nil];
    [editButton setAction:@selector(showEditAddon:)];
    [editButton setTarget:self];
}

- (void)showEditAddon:(id)sender
{
    [[itemAddon.popoverAddon contentViewController] setView:itemAddon.viewAddon];
    if ([itemAddon.popoverAddon isShown])
    {
        var ov = [self objectValue];
        ov.itemid = [itemAddon.itemidInput stringValue];
        ov.itemType = [itemAddon.itemType stringValue];
        ov.startDate = [itemAddon.startDate stringValue];
        ov.endDate = [itemAddon.endDate stringValue];
        ov.price = [itemAddon.price stringValue];
        ov.discountText = [itemAddon.discountText stringValue];
        [self setObjectValue:ov];
        [itemAddon.popoverAddon close];
    } else {
        [itemAddon.popoverAddon close];
        [itemAddon.popoverAddon showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [itemAddon.itemidInput setStringValue:[[self objectValue] itemid]];
        [itemAddon.itemType setStringValue:[[self objectValue] itemType]];
        [itemAddon.startDate setStringValue:[[self objectValue] startDate]];
        [itemAddon.endDate setStringValue:[[self objectValue] endDate]];
        [itemAddon.price setStringValue:[[self objectValue] price]];
        [itemAddon.discountText setStringValue:[[self objectValue] discountText]];
    }
}
@end

// SERVICE DEFINITION
@implementation DMServiceDefinition : COResource
{
    /* default ivars for couchdb */
    CPString coId @accessors();
    CPString coRev  @accessors();

    /* custom ivars */
    CPString servicetype  @accessors();
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
    return @"servicetype";
}
@end

// SERVICE
@implementation DMServiceItem : COResource
{
    /* default ivars for couchdb */
    CPString coId @accessors();
    CPString coRev  @accessors();

    CPString servicetype @accessors();
    CPString startDate @accessors();
    CPString endDate @accessors();
    CPString price @accessors();
    CPString discountText @accessors();
}

- (id)init
{
    self = [super init];
    if (self)
    {
        [self setServicetype:@"NEW"];
    }
    return self;
}

+ (id)couchId:(id)aItem
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (CPString)nameIdentifierString
{
    return @"servicetype";
}
@end

@implementation DMServiceItemCellView : CPTableCellView
{
    @outlet CPTextField servicetypeField;
}

- (void)awakeFromCib
{
    [servicetypeField bind:@"value"
               toObject:self
            withKeyPath:@"objectValue.servicetype"
                options:nil];
}
@end