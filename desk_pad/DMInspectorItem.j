@import <CouchResource/COResource.j>

@implementation DMInspectorItem : COResource
{
    /* default ivars for couchdb */
    CPString coId    @accessors;
    CPString coRev   @accessors;
}

+ (id)couchId
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

- (id)init
{
    self = [super init];
    if (self)
    {
        [self setVersion:1];
    }
    return self;
}

- (CPString)nameIdentifierString
{
    return @"coId";
}

@end
