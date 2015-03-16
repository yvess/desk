@import <CouchResource/COResource.j>
@import <CouchResource/COResourceVersioned.j>
@import <CouchResource/COCategories.j>
@import <CouchResource/COItemsParent.j>
@import <CouchResource/COSubItem.j>
@import <Foundation/CPMutableArray.j>


@implementation DMDomainA : COSubItem
{
    CPString host @accessors();
    CPString ip @accessors();
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
    return [CPString stringWithFormat:@"%@ : %@", host, ip];
}
@end


@implementation DMDomainCname : COSubItem
{
    CPString alias @accessors();
    CPString host @accessors();
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
  return [CPString stringWithFormat:@"%@ : %@", alias, host];
}
@end


@implementation DMDomainMx : COSubItem
{
    CPString host @accessors();
    CPString priority @accessors();
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
  return [CPString stringWithFormat:@"%@ : %@", host, priority];
}
@end


@implementation DMDomain : COResourceVersioned
{
    CPString coId          @accessors();
    CPString coRev         @accessors();
    CPString coAttachments @accessors();
    CPString prevActiveRev @accessors();
    CPString state         @accessors();

    CPString domain        @accessors();
    CPString nameservers   @accessors();
    // SOA
    CPString hostmaster    @accessors();
    CPString refresh       @accessors();
    CPString retry         @accessors();
    CPString expire        @accessors();
    CPString ttl           @accessors();

    //CPString client_id   @accessors();
    CPString clientId      @accessors();
    CPString templateId    @accessors();
    COItemsParent a        @accessors(readonly);
    COItemsParent cname    @accessors(readonly);
    COItemsParent mx       @accessors;
}

- (CPString)nameIdentifierString
{
    return @"domain";
}

- (CPString)transformLabel:(CPString) aLabel
{
    return [aLabel uppercaseString];
}

- (CPString)nameservers
{
    if ([self.nameservers className] == @"CPString")
    {
        return self.nameservers;
    } else {
        return [[self.nameservers items] componentsJoinedByString:@", "];
    }
}

- (JSObject)attributes
{
    var a_items = [[self a] items],
        cname_items = [[self cname] items],
        mx_items = [[self mx] items],
        a_array = [],
        cname_array = [],
        mx_array = [];
    if ([self nameservers])
    {
        var nameservers_array = [[self nameservers] componentsSeparatedByString:@","];
        if (nameservers_array)
        {
            nameservers_array = nameservers_array.map(
                function(item) { return item.trim(); }
            );
            nameservers_array.sort();
        }
    }

    [a_items enumerateObjectsUsingBlock:function(item) {
        a_array.push([item JSONFromObject]);
    }];

    [cname_items enumerateObjectsUsingBlock:function(item) {
        cname_array.push([item JSONFromObject]);
    }];

    [mx_items enumerateObjectsUsingBlock:function(item) {
        mx_array.push([item JSONFromObject]);
    }];

    var json = {},
        couchKeys = ["_id", "_rev", "_attachments", "prev_rev", "prev_active_rev", "state","domain", "nameservers", "hostmaster", "refresh",
                     "retry", "expire", "ttl", "client_id", "template_id", "a", "cname", "mx"],
        cappuccinoValues = [coId, coRev, coAttachments, prevRev, prevActiveRev, state, domain, nameservers_array, hostmaster, refresh,
                            retry, expire, ttl, clientId, templateId, a_array, cname_array, mx_array];

    for (var i = 0; i < couchKeys.length; i++)
    {
        if (cappuccinoValues[i])
        {
            json[couchKeys[i]] = cappuccinoValues[i];
        }
    }
    json['type'] = [[self class] underscoreName];
    return json;
}

- (id)init
{
    self = [super init];
    if (self)
    {
        a = [[COItemsParent alloc] initWithLabel: @"A"];
        cname = [[COItemsParent alloc] initWithLabel: @"CNAME"];
        mx = [[COItemsParent alloc] initWithLabel: @"MX"];
    }
    return self;
}

- (id)initFromCouch
{
    self = [self init];
    return self;
}

+ (id)resourceDidLoad:(CPString)aResponse
{
    var resource = [super resourceDidLoad: aResponse];
    if (resource)
    {
        [self addCouchVersion];
    }
    return resource;
}

@end
