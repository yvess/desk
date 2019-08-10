@implementation DMPopover : CPPopover
{
    CPButton editButton @accessors;
}
- (CPPopover)initWithButton:(CPButton)aButton
{
    if (self = [super init])
    {
        editButton = aButton;
    }
    [self setAnimates:NO];
    [self setBehavior:CPPopoverBehaviorSemitransient]; //CPPopoverBehaviorSemitransient, CPPopoverBehaviorTransient

    return self;
}

- (void)_close
{
    //console.log('CPPopover close DMSupport');
    //console.log([self editButton]);
    [editButton setTitle:@"edit"];
    [super _close];
}
@end
