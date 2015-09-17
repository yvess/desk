@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>
@import <CouchResource/COResource.j>

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

- (id)init
{
    self = [super init];
    if (self)
    {
        [self setName:@"email"];
        [self setProperty:@"prop"];
        [self setValue:@"new value"];
    }
    console.log(self);
    return self;
}
@end


@implementation DMPropertyCellView : CPTableCellView
{
    @outlet CPTextField valueText;
    @outlet CPPopUpButton namePUB;
    @outlet CPPopUpButton propertyPUB;
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
@end

@implementation DMServiceDefinition : COResource
{
    /* default ivars for couchdb */
    CPString coId @accessors();
    CPString coRev  @accessors();

    /* custom ivars */
    CPString serviceType  @accessors();
    CPArray packages  @accessors();
    CPDictionary addons @accessors();
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
