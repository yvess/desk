@import <CouchResource/COResource.j>

@implementation DMClient : COResource
{
    /* default ivars for couchdb */
    CPString coId    @accessors;
    CPString coRev   @accessors;

    /* custom ivars */
    CPNumber version   @accessors;
    CPString name      @accessors;
    CPString state     @accessors;
    CPString extcrmId  @accessors;
    CPString extcrmContactId    @accessors;
    CPString lastInvoiceEndDate @accessors;
    BOOL isBillable @accessors;
    CPString notes @accessors;
}

+ (id)couchId
{
    var cType = [[self class] underscoreName];
    return [CPString stringWithFormat:@"%@-%@", cType, [self nextUUID]];
}

+ (CPURL)resourcePath
{
    return [CPURL URLWithString:@"/api/" + [self underscoreName] + @"s"];
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
    return @"name";
}

- (CPString)selectorDestroy
{
    return @"markAsDeleted";
}
@end
