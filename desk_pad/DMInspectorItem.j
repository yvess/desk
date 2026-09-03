@import <CouchResource/COResource.j>

@implementation DMInspectorItem : COResource
{
    CPString hostname;
    CPString subType;
    CPString itemDomain;
    CPString itemType;
    CPString itemTitle;
    CPString itemPath;
    CPString itemVersion;
    CPString itemPackagesVersions;
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

+ (CPArray)allItemsFor:(CPObject) aModelClass
{
    return [aModelClass allWithParams:{} withPath:@"/api/inspector_items"];
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
    return @"itemDomain";
}

@end
