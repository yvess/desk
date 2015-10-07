@import <CouchResource/COResource.j>

@implementation DMTemplate : COResource
{
    /* default ivars for couchdb */
    CPString coId      @accessors;
    CPString coRev     @accessors;

    /* custom ivars */
    CPString name          @accessors;
    CPString templateType  @accessors;
}

- (CPString)nameIdentifierString
{
    return @"name";
}
@end
