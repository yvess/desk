@import <CouchResource/COResource.j>

@implementation DMProject : COResource
{
    /* default ivars for couchdb */
    CPString coId      @accessors();
    CPString coRev     @accessors();

    /* custom ivars */
    CPString name       @accessors();
    CPString clientId  @accessors();
}

- (CPString)nameIdentifierString
{
    return @"name";
}
@end
