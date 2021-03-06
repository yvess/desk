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
@import "DMClient.j"
@import "DMClientViewController.j"
@import "DMDomain.j"
@import "DMDomainViewController.j"
@import "DMOrder.j"
@import "DMInspectorItem.j"
@import "DMInspectorViewController.j"

var defaultGrowlCenter = nil;

@implementation AppController : CPObject
{
    CPWindow             theWindow; //this "outlet" is connected automatically by the Cib

    @outlet              CPTabView mainTabView;
    @outlet              CPButton clientsSwitchButton;
    @outlet              CPButton domainSwitchButton;
    @outlet              CPButton inspectorSwitchButton;
    @outlet              CPButton orderButton;

    DMClientViewController    clientViewController;
    DMDomainViewController    domainViewController;
    DMInspectorViewController inspectorViewController;
    CPSet                popovers;
    TNGrowlCenter        growlCenter;
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
    case @"Inspector":
        [mainTabView selectTabViewItemAtIndex:2];
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

    if (!defaultGrowlCenter)
    {
        defaultGrowlCenter = [TNGrowlCenter defaultCenter];
    }

    var clientVC = [[DMClientViewController alloc]
                    initWithCibName:@"ClientView"
                    bundle:nil
                    modelClass:[DMClient class]
                    growlCenter:defaultGrowlCenter
        ],
        domainVC = [[DMDomainViewController alloc]
                    initWithCibName:@"DomainView"
                    bundle:nil
                    modelClass:[DMDomain class]
                    growlCenter:defaultGrowlCenter
                    clients:[clientVC items]
                    clientLookup:[clientVC itemLookup]
        ],
        inspectorVC = [[DMInspectorViewController alloc]
                    initWithCibName:@"InspectorView"
                    bundle:nil
                    modelClass:[DMInspectorItem class]
                    growlCenter:defaultGrowlCenter
        ];

    self.clientViewController = clientVC;
    self.domainViewController = domainVC;
    self.inspectorViewController = inspectorVC;

    [[mainTabView tabViewItemAtIndex:0] setView:[clientVC view]];
    [[mainTabView tabViewItemAtIndex:1] setView:[domainVC view]];
    [[mainTabView tabViewItemAtIndex:2] setView:[inspectorVC view]];
}

- (void)applicationDidFinishLaunching:(CPNotification)aNotification
{
    // This is called when the application is done loading.
    [clientsSwitchButton setAction:@selector(switchTabFromButton:)];
    [domainSwitchButton setAction:@selector(switchTabFromButton:)];
    [inspectorSwitchButton setAction:@selector(switchTabFromButton:)];
    [orderButton setAction:@selector(pushUpdate)];
    [orderButton setTarget:self];

    [mainTabView selectTabViewItemAtIndex:0];
    [self switchTabFromButton:@"Clients"];

    [defaultGrowlCenter setView:mainTabView];

    var doNotificationOrdersDone = function(data) {
        var title = @"order processed",
            message = [CPString stringWithFormat:@"id: %@ \nstate:%@ \nsender:%@", data.id, data.doc.state, data.doc.sender];
        if (data.doc.hasOwnProperty('text'))
        {
            message = [CPString stringWithFormat:@"%@\n\n%@", message, data.doc.text];
        }
        if (data.doc.state == 'error')
        {
            [defaultGrowlCenter pushNotificationWithTitle:title message:message icon:TNGrowlIconError];
        } else {
            [defaultGrowlCenter pushNotificationWithTitle:title message:message];
        }
    }

    var doNotificationOrdersNew = function(data) {
        var title = @"new order in queue",
            message = [CPString stringWithFormat:@"id: %@ \nstate:%@ \nsender:%@", data.id, data.doc.state, data.doc.sender];
        if (data.doc.hasOwnProperty('text'))
        {
            message = [CPString stringWithFormat:@"%@\n\n%@", message, data.doc.text];
        }
        [defaultGrowlCenter pushNotificationWithTitle:title message:message];
    }

    if (!!window.EventSource)
    {
        var sourceOrdersDone = new EventSource("/orders/done/?since=now");
        sourceOrdersDone.addEventListener('message', function(e) {
          var data = JSON.parse(e.data);
          doNotificationOrdersDone(data);
          if (data.doc['type'] == 'order')
          {
            var currentDomainIndex = [domainViewController selectionIndex];
            [domainViewController reloadItems];
            [domainViewController setSelectionIndex:currentDomainIndex];
          }
        }, false);

        var sourceOrdersNew = new EventSource("/orders/new/?since=now");
        sourceOrdersNew.addEventListener('message', function(e) {
          var data = JSON.parse(e.data);
          doNotificationOrdersNew(data);
        }, false);

        sourceOrdersNew.addEventListener('open', function(e) {
          // Connection was opened.
        }, false);

        sourceOrdersNew.addEventListener('error', function(e) {
          if (e.readyState == EventSource.CLOSED)
          {
            // Connection was closed.
            console.log("eventsource errror");
          }
        }, false);
    }
}

@end
