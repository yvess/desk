@import <Foundation/CPObject.j>

@implementation DMServicePackageProperty : CPObject
{
    CPString name     @accessors();
    CPString item     @accessors();
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
        [self setName:@"MEW"];
        [self setItem:@"xxx"];
    }
    return self;
}

@end
