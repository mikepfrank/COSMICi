#|******************************************************************************
#|                                  TOP OF FILE
#|******************************************************************************
#|
#|      FILE NAME:      publisher.py            [Python module source file]
#|
#|      DESCRIPTION:
#|
#|          This is a general purpose event-notification facility,
#|          framed in terms of a publisher/subscriber metaphor.
#|
#|          The metaphor is: A "publisher" object publishes a set of
#|          "magazine titles", which are message types.  A subscriber
#|          takes out a "subscription" to the titles it is interested
#|          in, or to all magazines published by that publisher.  Then,
#|          whenever a new "issue" of the "magazine" is "published," a
#|          copy of it is "delivered" to each of the "subscribers"
#|          through their "addresses," which are simply callbacks.
#|          Each "issue" has some arbitrary "content" (data).
#|
#|          There is an option to subscribe to all of the publisher's
#|          titles, which includes titles not yet issued.
#|
#|          Multithreaded operation is not required, but it can be
#|          implemented if desired by making the callback be a method
#|          to pass the issue to a worker thread's .do() method.
#|
#|      INTENDED USE:
#|
#|          What I'm thinking is that the GPS model/proxy will publish
#|          a different "magazine" for each type of incoming GPS message.
#|          Then the Timekeeper module can subscribe to the message types
#|          that it cares about to ensure it receives all the time-related
#|          data, and store it in a database and reference it to calculate
#|          absolute times for input events.  (The Timekeeper module is not
#|          yet written, however.)
#|
#|      PUBLIC CLASSES:
#|
#|          Issue - An object that has a '.title' (type) and '.content' (data).
#|
#|          Publisher - Keeps track of who is subscribed to which titles.
#|              Distributes new issues to subscribers upon publication.
#|
#|      USAGE EXAMPLE:
#|
#|          marvel = Publisher()
#|
#|          def fanboy(issue):
#|              print("Fanboy is reading issue #%d of %s.\n" % (issue.content, issue.title))
#|
#|          marvel.subscribe(fanboy, 'Spider-Man')
#|
#|          marvel.publish(Issue('Spider-Man', 1))
#|
#|          dc = Publisher()
#|          dc.subscribeAll(fanboy)
#|
#|          dc.publish(Issue('Batman', 1))
#|
#|      VERSION HISTORY:
#|          v1.0, 3/2/12 (MPF) - Initial version created & unit-tested.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

import threading

__all__ = ['Issue', 'Publisher']

class   Issue:
    def __init__(this, title, content):
        this.title = title
        this.content = content

class   Publisher:

    def __init__(this):
        this._lock = threading.RLock()
        with this._lock:
            this._subscriptions = dict()    # key=title, value=list of subscribers

    def hasTitle(this, title):
        with this._lock:
            if title not in this._subscriptions:
                this._subscriptions[title] = []     # initialize to empty list of subscribers

    def subscribe(this, address, title):
        with this._lock:
            this.hasTitle(title)
            this._subscriptions[title] = this._subscriptions[title] + [address]

    def subscribeAll(this, address):
        this.subscribe(address, '__ALL__')

    def deliver(this, issue, addr):
        addr(issue)                     # assume addr's a callable and call it
    
    def publish(this, issue):
        title = issue.title
        this.hasTitle(title)
        this.hasTitle('__ALL__')
        for addr in this._subscriptions[title] + this._subscriptions['__ALL__']:
            this.deliver(issue, addr)

def _module_unit_test():

    marvel = Publisher()

    def fanboy(issue):
        print("Fanboy is reading %s #%d." % (issue.title, issue.content))

    marvel.subscribe(fanboy, 'Spider-Man')

    marvel.publish(Issue('Spider-Man', 1))

    def fangirl(issue):
        print("Fangirl is reading %s #%d." % (issue.title, issue.content))

    marvel.subscribeAll(fangirl)
    
    marvel.publish(Issue('Spider-Man', 2))
    marvel.publish(Issue('She-Hulk', 1))

#|^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#|      END FILE:   publisher.py
#|******************************************************************************
