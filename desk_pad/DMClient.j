@import <CouchResource/COResource.j>

@implementation DMClient : COResource
{
    /* default ivars for couchdb */
    CPString coId    @accessors();
    CPString coRev   @accessors();

    /* custom ivars */
    CPString name     @accessors();
    CPString city     @accessors();
}

- (CPString)nameIdentifierString
{
    return @"name";
}
@end
