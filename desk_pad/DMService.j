@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>

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
