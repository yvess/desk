@import <CouchResource/COResource.j>

@implementation DMQueue : COResource
{
    /* default ivars for couchdb */
    CPString coId      @accessors();
    CPString coRev     @accessors();

    /* custom ivars */
    CPString date     @accessors();
	CPString user     @accessors();
	CPString sender   @accessors();
}

- (CPString)nameIdentifierString
{
    return @"date";
}
@end
