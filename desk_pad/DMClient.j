@import <CouchResource/COResource.j>

@implementation DMClient : COResource
{
    /* default ivars for couchdb */
    CPString coId    @accessors();
    CPString coRev   @accessors();

    /* custom ivars */
    CPString name     @accessors();
    CPString crmId    @accessors();
    BOOL isBillable @accessors();
}

+ (id)couchId:(id)aItem
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (CPString)nameIdentifierString
{
    return @"name";
}
@end
