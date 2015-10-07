@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>
@import <CouchResource/COResource.j>

var servicePropertyNamesArray = [[CPMutableArray alloc] init],
    itemIncluded = {},
    itemAddon = {},
    serviceItem = {};

// Service Properties

@implementation DMServicePackageProperty : CPObject
{
    CPString name     @accessors;
    CPString property @accessors;
    CPString value    @accessors;
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
    CPString itemid @accessors;
    CPString itemType @accessors;
    CPString rowtitle @accessors(readonly);
    CPString startDate @accessors;
    CPString endDate @accessors;
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


- (CPString)rowtitle
{
    var title = @"";
    if ([self itemType] && [self itemType] != @"NEW")
    {
        title += [self itemType] + @": ";
    }
    if ([self itemid] != @"")
    {
        title += [self itemid];
    }
    return title;
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
    withKeyPath:@"objectValue.rowtitle"
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
        if (ov.itemid == @"NEW")
        {
            ov.itemid = @"";
        }
        ov.itemType = [itemIncluded.itemType titleOfSelectedItem];
        ov.startDate = [itemIncluded.startDate stringValue];
        ov.endDate = [itemIncluded.endDate stringValue];
        [self setObjectValue:ov];
        [itemIncluded.popoverIncluded close];
    } else {
        [itemIncluded.popoverIncluded close];
        [itemIncluded.popoverIncluded showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
        [itemIncluded.itemidInput setStringValue:[[self objectValue] itemid]];
        if ([[self objectValue] itemType])
        {
            [itemIncluded.itemType setTitle:[[self objectValue] itemType]];
        }
        [itemIncluded.startDate setStringValue:[[self objectValue] startDate]];
        [itemIncluded.endDate setStringValue:[[self objectValue] endDate]];
    }
}
@end

// ADDON ITEM

@implementation DMAddonServiceItem : CPObject
{
    CPString itemid   @accessors;
    CPString itemType @accessors;
    CPString rowtitle @accessors(readonly);
    CPString startDate @accessors;
    CPString endDate @accessors;
    CPString price @accessors;
    CPString discountText @accessors;
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

- (CPString)rowtitle
{
    var title = @"";
    if ([self itemType] && [self itemType] != @"NEW")
    {
        title += [self itemType] + @": ";
    }
    if ([self itemid] != @"")
    {
        title += [self itemid];
    }
    return title;
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
    withKeyPath:@"objectValue.rowtitle"
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
        ov.itemType = [itemAddon.itemType titleOfSelectedItem];
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
        if ([[self objectValue] itemType])
        {
            [itemAddon.itemType setTitle:[[self objectValue] itemType]];
        }
        [itemAddon.startDate setStringValue:[[self objectValue] startDate]];
        [itemAddon.endDate setStringValue:[[self objectValue] endDate]];
        [itemAddon.price setStringValue:[[self objectValue] price]];
        [itemAddon.discountText setStringValue:[[self objectValue] discountText]];
    }
}
@end

// SERVICE
@implementation DMService : COResource
{
    /* default ivars for couchdb */
    CPString coId @accessors;
    CPString coRev  @accessors;
    CPString clientId @accessors;

    CPString serviceType @accessors;
    CPString packageType @accessors;
    CPString startDate @accessors;
    CPString endDate @accessors;
    CPString price @accessors;
    CPString discountText @accessors;

    CPMutableArray packagePropertiesItems @accessors;
    CPMutableArray includedServiceItems @accessors;
    CPMutableArray addonServiceItems @accessors;
}

+ (id)couchId
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (id)init
{
    self = [super init];
    if (self)
    {
        [self setServiceType:@"NEW"];
    }
    return self;
}

- (CPString)nameIdentifierString
{
    return @"serviceType";
}

- (id)valueForObject:(id)value withName:(CPString)attributeName
{
    if ([value className] == @"_CPJavaScriptArray")
    {
        switch (attributeName)
        {
            case "addonServiceItems":
                var valueObjectArray = [self arrayForObjects:value withClass:DMAddonServiceItem];
                break;
            case "includedServiceItems":
                var valueObjectArray = [self arrayForObjects:value withClass:DMIncludedServiceItem];
                break;
            case "packagePropertiesItems":
                var valueObjectArray = [self arrayForObjects:value withClass:DMServicePackageProperty];
                break;
            default:
                console.log("### no match found", attributeName);
        }
        return valueObjectArray;
    } else {
        //console.log([value className]);
    }
}

- (JSObject)attributes
{
    var json = {},
        classIvars = class_copyIvarList([self class]);
    var addObjectToArray = function (keys, item, array)
        {
            var object = {};
            keys.forEach(function(key){
                var value = item[key];
                if (value)
                {
                    object[key] = value;
                }
            });
            if (object != {})
            {
                array.push(object);
            }
        };
    [classIvars enumerateObjectsUsingBlock:function(ivar) {
        var attr = [[CPString stringWithFormat:@"%@", ivar.name] underscoreString],
            value = [self performSelector:CPSelectorFromString(ivar.name)];

        switch (ivar.name)
        {
            case 'coId':
                attr = "_id";
                break;
            case 'coRev':
                attr = "_rev"
                break;
            case 'packagePropertiesItems':
                var propertyArray = [];
                [value enumerateObjectsUsingBlock:function(item) {
                    addObjectToArray(
                        ['name', 'property', 'value'],
                         item, propertyArray
                    );
                }];
                value = propertyArray;
                break;
            case 'includedServiceItems':
                var includedArray = [];
                [value enumerateObjectsUsingBlock:function(item) {
                    addObjectToArray(
                        ['itemid', 'itemType', 'startDate', 'endDate'],
                         item, includedArray
                    );
                }];
                value = includedArray;
                break;
            case 'addonServiceItems':
                var addonArray = [];
                [value enumerateObjectsUsingBlock:function(item) {
                    addObjectToArray(
                        ['itemid', 'itemType', 'startDate', 'endDate', 'price',
                         'discountText'], item, addonArray
                    );
                }];
                value = addonArray;
                break;
        }

        if (value != null && value != "" && value != [])
        {
            json[attr] = value;
        }
    }];
    json['type'] = [[self class] underscoreName];
    return json;
}
@end

@implementation DMServiceCellView : CPTableCellView
{
    @outlet CPTextField serviceTypeField;
    @outlet CPButton editButton;
    @outlet CPButton delButton;
}

+ (id)serviceItem
{
    return serviceItem;
}

- (void)awakeFromCib
{
    [serviceTypeField bind:@"value"
               toObject:self
            withKeyPath:@"objectValue.serviceType"
                options:nil];
    [editButton setAction:@selector(showEdit:)];
    [editButton setTarget:self];
    [delButton setAction:@selector(removeService:)];
    [delButton setTarget:self];
}

- (void)showEdit:(id)sender
{
    [serviceItem.addServiceButton setHidden:YES];
    var ov = [self objectValue];
    if ([serviceItem.popoverService isShown])
    {
        ov.serviceType = [serviceItem.serviceType titleOfSelectedItem];
        ov.packageType = [serviceItem.packageType titleOfSelectedItem];
        ov.packagePropertiesItems = [[CPMutableArray alloc] initWithArray:[serviceItem.packagePropertiesAC contentArray] copyItems:YES];
        ov.includedServiceItems = [[CPMutableArray alloc] initWithArray:[serviceItem.includedServiceAC contentArray] copyItems:YES];
        ov.addonServiceItems = [[CPMutableArray alloc] initWithArray:[serviceItem.addonServiceAC contentArray] copyItems:YES];
        ov.startDate = [serviceItem.startDate stringValue];
        ov.endDate = [serviceItem.endDate stringValue];
        ov.price = [serviceItem.price stringValue];
        ov.discountText = [serviceItem.discountText stringValue];
        [self setObjectValue:ov];
        [serviceItem.popoverService close];
    } else {
        [serviceItem.clientViewController updateServiceDefinition];
        [serviceItem.serviceType selectItemWithTitle:ov.serviceType];
        [serviceItem.packageType selectItemWithTitle:ov.packageType];
        [serviceItem.packagePropertiesAC setContent:ov.packagePropertiesItems];
        [serviceItem.includedServiceAC setContent:ov.includedServiceItems];
        [serviceItem.addonServiceAC setContent:ov.addonServiceItems];
        [serviceItem.startDate setStringValue:ov.startDate ? ov.startDate : @""];
        [serviceItem.endDate setStringValue:ov.endDate ? ov.endDate : @""];
        [serviceItem.price setStringValue:ov.price ? ov.price : @""];
        [serviceItem.discountText setStringValue:ov.discountText ? ov.discountText : @""];

        [serviceItem.popoverService showRelativeToRect:nil ofView:sender preferredEdge:CPMinYEdge];
    }
}

- (void)removeService:(id)sender
{
    var item = [self objectValue];
    [serviceItem.servicesAC removeObject:item];
    [item destroy];
    item = nil;
}
@end

// SERVICE DEFINITION
@implementation DMServiceDefinition : COResource
{
    /* default ivars for couchdb */
    CPString coId @accessors;
    CPString coRev  @accessors;

    /* custom ivars */
    CPString serviceType  @accessors;
    CPArray packages @accessors;
    CPDictionary addons @accessors;
    CPDictionary properties @accessors;
}

+ (id)couchId
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (CPString)nameIdentifierString
{
    return @"serviceType";
}
@end
