/*
 * AppController.j
 * desk_pad
 *
 * Created by You on May 18, 2011.
 * Copyright 2011, Your Company All rights reserved.
 */

@import <Foundation/CPObject.j>
@import <Foundation/CPSet.j>
@import <AppKit/CPTableView.j>
@import <AppKit/CPTextField.j>
@import <AppKit/CPPopUpButton.j>
@import <AppKit/CPButtonBar.j>
@import <AppKit/CPTabView.j>
@import <GrowlCappuccino/GrowlCappuccino.j>
@import <CouchResource/COCategories.j>
@import <CouchResource/COViewController.j>
@import "DMClient.j"
@import "DMClientViewController.j"
@import "DMDomain.j"
@import "DMDomainViewController.j"
@import "DMOrder.j"

@implementation AppController : CPObject
{
    CPWindow              theWindow; //this "outlet" is connected automatically by the Cib

    @outlet              CPTabView mainTabView;
    @outlet              CPButton clientsSwitchButton;
    @outlet              CPButton domainSwitchButton;
    @outlet              CPButton orderButton;

    DMClientViewController clientViewController;
    DMDomainViewController domainViewController;
    CPSet                popovers;
}

- (void)switchTabFromButton:(id)sender
{
    [window.popovers makeObjectsPerformSelector:@selector(close)];
    var activeTab = [sender class] == [CPString class] ? sender : [sender title];
    switch (activeTab)
    {
    case @"Clients":
        [mainTabView selectTabViewItemAtIndex:0];
        break;
    case @"DNS":
        [mainTabView selectTabViewItemAtIndex:1];
        break;
    }
}
- (void)pushUpdate
{
    //console.log([CPDate date]);
    var order = [[DMOrder alloc] init];
    //[order setDate:[CPString stringWithFormat:@"%@", [[CPDate date] description]]]; // [CPDate date]
    [order setDate:[CPString stringWithFormat:@"%@", new Date().toISOString()]];
    [order setCoId:[DMOrder couchId]];
    [order setSender:@"pad"];
    [order setState:@"new_pre"];
    [order save];
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

- (void)awakeFromCib
{
    [theWindow setFullPlatformWindow:YES];
    popovers = [[CPSet alloc] init];
    window.popovers = popovers;

    var clientVC = [[DMClientViewController alloc]
                    initWithCibName:@"ClientView" bundle:nil modelClass:[DMClient class]],
        domainVC = [[DMDomainViewController alloc]
                    initWithCibName:@"DomainView" bundle:nil
                    modelClass:[DMDomain class] clients:[clientVC items]
                    clientLookup:[clientVC itemLookup]];

    self.clientViewController = clientVC;
    self.domainViewController = domainVC;

    [[mainTabView tabViewItemAtIndex:0] setView:[clientVC view]];
    [[mainTabView tabViewItemAtIndex:1] setView:[domainVC view]];
}

- (void)applicationDidFinishLaunching:(CPNotification)aNotification
{
    // This is called when the application is done loading.
    [clientsSwitchButton setAction:@selector(switchTabFromButton:)];
    [domainSwitchButton setAction:@selector(switchTabFromButton:)];
    [orderButton setAction:@selector(pushUpdate)];
    [orderButton setTarget:self];

    [mainTabView selectTabViewItemAtIndex:0];
    [self switchTabFromButton:@"Clients"];

    var growlCenter = [TNGrowlCenter defaultCenter];

    [growlCenter setView:mainTabView];
    var doNotification = function(data) {
        console.log("doNotification");
        var message = [CPString stringWithFormat:@"id: %@\nsender:%@", data.id, data.doc.sender];
        [growlCenter pushNotificationWithTitle:@"order done" message:message];
    }
    domainViewController.growlCenter = growlCenter;
    clientViewController.growlCenter = growlCenter;

    if (!!window.EventSource)
    {
        var source = new EventSource("/orders/done/?since=now");
        source.addEventListener('message', function(e) {
          console.log("order updated");
          var data = JSON.parse(e.data);
          doNotification(data);
          if (data.doc['type'] == 'order')
          {
            var currentDomainIndex = [domainViewController selectionIndex];
            [domainViewController reloadItems];
            [domainViewController setSelectionIndex:currentDomainIndex];
          }
        }, false);

        source.addEventListener('open', function(e) {
          // Connection was opened.
        }, false);

        source.addEventListener('error', function(e) {
          if (e.readyState == EventSource.CLOSED)
          {
            // Connection was closed.
            console.log("eventsource errror");
          }
        }, false);
    }
}

@end
