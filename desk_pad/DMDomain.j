@import <CouchResource/COResource.j>
@import <CouchResource/COCategories.j>
@import <CouchResource/COItemsParent.j>
@import <CouchResource/COSubItem.j>
@import <Foundation/CPMutableArray.j>


@implementation DMDomainA : COSubItem
{
    CPString host @accessors;
    CPString ip @accessors;
}
- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
    return [CPString stringWithFormat:@"%@ : %@", host, ip];
}
@end

@implementation DMDomainAaaa : COSubItem
{
    CPString host @accessors;
    CPString ipv6 @accessors;
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
    return [CPString stringWithFormat:@"%@ : %@", host, ipv6];
}
@end


@implementation DMDomainCname : COSubItem
{
    CPString alias @accessors;
    CPString host @accessors;
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
  return [CPString stringWithFormat:@"%@ : %@", alias, host];
}
@end


@implementation DMDomainMx : COSubItem
{
    CPString host @accessors;
    CPNumber priority @accessors;
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
  return [CPString stringWithFormat:@"%@ : %@", host, priority];
}
@end

@implementation DMDomainTxt : COSubItem
{
    CPString name @accessors;
    CPString content @accessors;
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
  return [CPString stringWithFormat:@"%@ : %@", name, content];
}
@end

@implementation DMDomainSrv : COSubItem
{
    CPString name @accessors;
    CPNumber priority @accessors;
    CPNumber weight @accessors;
    CPNumber port @accessors;
    CPString targethost @accessors;
}

- (CPString)objectValueForOutlineColumn:(CPString)aTableColumn
{
  return [CPString stringWithFormat:@"%@ : %@", name, targethost];
}
@end

@implementation DMDomain : COResource
{
    CPString coId          @accessors;
    CPString coRev         @accessors;
    CPString coAttachments @accessors;
    CPNumber version       @accessors;
    CPString activeRev     @accessors;
    CPString prevActiveRev @accessors;
    CPString state         @accessors;

    CPString domain        @accessors;
    CPString nameservers   @accessors;
    // SOA
    CPString hostmaster    @accessors;
    CPString refresh       @accessors;
    CPString retry         @accessors;
    CPString expire        @accessors;
    CPString ttl           @accessors;

    //CPString client_id   @accessors;
    CPString clientId      @accessors;
    CPString templateId    @accessors;
    COItemsParent a        @accessors(readonly);
    COItemsParent aaaa     @accessors(readonly);
    COItemsParent cname    @accessors(readonly);
    COItemsParent mx       @accessors(readonly);
    COItemsParent txt      @accessors(readonly);
    COItemsParent srv      @accessors(readonly);
}

- (CPString)nameIdentifierString
{
    return @"domain";
}

- (CPString)selectorDestroy
{
    return @"markForDeletion";
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
        aaaa_items = [[self aaaa] items],
        cname_items = [[self cname] items],
        mx_items = [[self mx] items],
        txt_items = [[self txt] items],
        srv_items = [[self srv] items],
        a_array = [],
        aaaa_array = [],
        cname_array = [],
        mx_array = [],
        txt_array = [],
        srv_array = [];

    function createCompare(sortkey) {
        var compare = function (x, y) {
            if (x[sortkey] < y[sortkey])
                return -1;
            if (x[sortkey] > y[sortkey])
                return 1;
            return 0;
        }
        return compare;
    }

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
    a_array.sort(createCompare('host'));

    [aaaa_items enumerateObjectsUsingBlock:function(item) {
        aaaa_array.push([item JSONFromObject]);
    }];
    aaaa_array.sort(createCompare('host'));

    [cname_items enumerateObjectsUsingBlock:function(item) {
        cname_array.push([item JSONFromObject]);
    }];
    cname_array.sort(createCompare('alias'));

    [mx_items enumerateObjectsUsingBlock:function(item) {
        mx_array.push([item JSONFromObject]);
    }];
    mx_array.sort(createCompare('host'));

    [txt_items enumerateObjectsUsingBlock:function(item) {
        txt_array.push([item JSONFromObject]);
    }];
    txt_array.sort(createCompare('name'));

    [srv_items enumerateObjectsUsingBlock:function(item) {
        srv_array.push([item JSONFromObject]);
    }];
    srv_array.sort(createCompare('name'));

    var json = {},
        couchKeys = ["_id", "_rev", "_attachments", "version", "active_rev", "prev_active_rev", "state","domain", "nameservers", "hostmaster", "refresh",
                     "retry", "expire", "ttl", "client_id", "template_id", "a", "aaaa", "cname", "mx", "txt", "srv"],
        cappuccinoValues = [coId, coRev, coAttachments, version, activeRev, prevActiveRev, state, domain, nameservers_array, hostmaster, refresh,
                            retry, expire, ttl, clientId, templateId, a_array, aaaa_array, cname_array, mx_array, txt_array, srv_array];

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
        a = [[COItemsParent alloc] initWithLabel: @"A"];
        aaaa = [[COItemsParent alloc] initWithLabel: @"AAAA"];
        cname = [[COItemsParent alloc] initWithLabel: @"CNAME"];
        mx = [[COItemsParent alloc] initWithLabel: @"MX"];
        txt = [[COItemsParent alloc] initWithLabel: @"TXT"];
        srv = [[COItemsParent alloc] initWithLabel: @"SRV"];
        [self setVersion:1];
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
