@import <CouchResource/COResource.j>

@implementation DMClient : COResource
{
    /* default ivars for couchdb */
    CPString coId    @accessors();
    CPString coRev   @accessors();

    /* custom ivars */
    CPString name     @accessors();
    CPString extcrmId    @accessors();
    CPString lastInvoiceEndDate @accessors();
    BOOL isBillable @accessors();
}

+ (id)couchId
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (CPString)nameIdentifierString
{
    return @"name";
}
@end
