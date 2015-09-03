@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>

@implementation DMServicePackageProperty : CPObject
{
    CPString name     @accessors();
    CPString item     @accessors();
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
        [self setItem:@"xxx"];
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
}
@end
