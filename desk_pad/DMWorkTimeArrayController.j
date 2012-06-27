@import <AppKit/CPArrayController.j>

@implementation DMWorkTimeArrayController : CPArrayController
{
}

- (void)remove:(id)sender
{
    [[CPNotificationCenter defaultCenter] postNotificationName:@"DMRemoveTableRow" object:[self selectedObjects]];
    [self removeObjects:[[self arrangedObjects] objectsAtIndexes:[self selectionIndexes]]];
}

- (void)insert:(id)sender
{
    {
        if (![self canInsert])
            return;

        var newObject = [[DMWorkTime alloc] initWithCurrentDate];
        [self addObject:newObject];
    }
    [[CPNotificationCenter defaultCenter] postNotificationName:@"DMAddTableRow" object:[self selectedObjects]];
}

@end
