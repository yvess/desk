@import <Foundation/CPObject.j>

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
