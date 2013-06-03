/*
 * AppController.j
 * desk_pad
 *
 * Created by You on May 18, 2011.
 * Copyright 2011, Your Company All rights reserved.
 */

@import <Foundation/CPObject.j>
@import <AppKit/CPTableView.j>
@import <AppKit/CPTextField.j>
@import <AppKit/CPPopUpButton.j>
@import <AppKit/CPButtonBar.j>
@import <GrowlCappuccino/GrowlCappuccino.j>

@import <CouchResource/COViewController.j>
@import "DMClient.j"
@import "DMClientViewController.j"
@import "DMProject.j"
@import "DMProjectViewController.j"
@import "DMWorkTime.j"
@import "DMWorkTimeViewController.j"
@import "DMDns.j"
@import "DMDnsViewController.j"
@import "DMQueue.j"
//@import "DMDnsViewController.j"

@implementation AppController : CPObject
{
    CPWindow              theWindow; //this "outlet" is connected automatically by the Cib

/*    CPMutableArray        workTimes;
    @outlet              WorkTimeArrayController workTimeArrayController;
    @outlet              CPTableView workTimesTable;*/

    @outlet              CPTabView mainTabView;
    @outlet              CPButton clientsSwitchButton;
    @outlet              CPButton projectsSwitchButton;
    @outlet              CPButton workTimesSwitchButton;
    @outlet              CPButton dnsSwitchButton;
    @outlet              CPButton queueButton;

}

- (void)switchTabFromButton:(id)sender
{
    var activeTab = [sender class] == [CPString class] ? sender : [sender title];
    switch (activeTab)
    {
    case @"Clients":
        [mainTabView selectTabViewItemAtIndex:0];
        break;
    case @"Projects":
        [mainTabView selectTabViewItemAtIndex:1];
        break;
    case @"WorkTimes":
        [mainTabView selectTabViewItemAtIndex:2];
        break;
    case @"DNS":
        [mainTabView selectTabViewItemAtIndex:3];
        break;
    }
}
- (void)pushUpdate
{
    //console.log([CPDate date]);
    var queue = [DMQueue new];
    [queue setDate:[CPString stringWithFormat:@"%@", [[CPDate date] description]]]; // [CPDate date]
    [queue setCoId:[DMQueue couchId:queue]];
    [queue setSender:@"pad"];
    [queue setState:@"new"];
    [queue save];
}

- (void)observeValueForKeyPath:(CPString)aKeyPath
        ofObject:(id)anObject
        change:(CPDictionary)aChange
        context:(id)aContext
{
    var item = [[anObject arrangedObjects] objectAtIndex:[anObject selectionIndex]],
        new_value = [aChange valueForKey:@"CPKeyValueChangeNewKey"],
        old_value = [aChange valueForKey:@"CPKeyValueChangeOldKey"];
}

/*! Notification responder of DMRemoveTableRow
    @param aNotification the received notification. This notification will contains as object the row
*/
/*- (void)tableRowRemoved:(CPNotification)aNotification
{

    var row = [[aNotification object] lastObject];
    console.log("remove", row);
    if ([row coId])
    {
        [row destroy]; // TODO remove itesm with space propogate error to interface
    }
}*/

- (void)awakeFromCib
{
    /*[[CPNotificationCenter defaultCenter]
        addObserver:self
        selector:@selector(tableRowRemoved:)
        name:@"DMRemoveTableRow" object:nil];*/

    [theWindow setFullPlatformWindow:YES];

    var clientViewController = [[DMClientViewController alloc]
                                //[COViewController alloc]
                                initWithCibName:@"ClientView"
                                bundle:nil //],
                                modelClass:[DMClient class]], //,
        // projectViewController = [[DMProjectViewController alloc]
        //                         initWithCibName:@"ProjectView"
        //                         bundle:nil
        //                         modelClass:[DMProject class]
        //                         clients:[clientViewController items]
        //                         clientLookup:[clientViewController itemLookup]],
        // workTimeViewController = [[DMWorkTimeViewController alloc]
        //                         initWithCibName:@"WorkTimeView"
        //                         bundle:nil
        //                         modelClass:[DMWorkTime class]],
        dnsViewController = [[DMDnsViewController alloc]
                                initWithCibName:@"DnsView"
                                bundle:nil
                                modelClass:[DMDns class]
                                clients:[clientViewController items]
                                clientLookup:[clientViewController itemLookup]];

    [[mainTabView tabViewItemAtIndex:0] setView:[clientViewController view]];
    // [[mainTabView tabViewItemAtIndex:1] setView:[projectViewController view]];
    // [[mainTabView tabViewItemAtIndex:2] setView:[workTimeViewController view]];
    [[mainTabView tabViewItemAtIndex:3] setView:[dnsViewController view]];
}

- (void)applicationDidFinishLaunching:(CPNotification)aNotification
{

    // This is called when the application is done loading.
    [clientsSwitchButton setAction:@selector(switchTabFromButton:)];
    // [projectsSwitchButton setAction:@selector(switchTabFromButton:)];
    // [workTimesSwitchButton setAction:@selector(switchTabFromButton:)];
    [dnsSwitchButton setAction:@selector(switchTabFromButton:)];
    [queueButton setAction:@selector(pushUpdate)];
    [queueButton setTarget:self];

    [mainTabView selectTabViewItemAtIndex:0];
    [self switchTabFromButton:@"Clients"];

    var growl = [TNGrowlCenter defaultCenter];

    [growl setView:mainTabView];
    var doNotification = function(data) {
        var message = [CPString stringWithFormat:@"id:\n%@ \n\nsender:%@", data.id, data.doc.sender];
        [growl pushNotificationWithTitle:@"queue done" message:message];
    }

    if (!!window.EventSource)
    {
        var source = new EventSource("/queue/changes?since=now");
        source.addEventListener('message', function(e) {
          var data = JSON.parse(e.data);
          doNotification(data)
        }, false);

        source.addEventListener('open', function(e) {
          // Connection was opened.
        }, false);

        source.addEventListener('error', function(e) {
          if (e.readyState == EventSource.CLOSED)
          {
            // Connection was closed.
          }
        }, false);
    }
}

@end
