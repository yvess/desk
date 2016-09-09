@import <CouchResource/COResource.j>

@implementation DMOrder : COResource
{
    /* default ivars for couchdb */
    CPString coId      @accessors;
    CPString coRev     @accessors;

    /* custom ivars */
    CPString date     @accessors;
    CPString user     @accessors;
    CPString sender   @accessors;
    CPString state    @accessors;
}

+ (id)couchId
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (CPString)nameIdentifierString
{
    return @"date";
}

- (CPString)selectorDestroy
{
    return @"markForDeletion";
}
@end
