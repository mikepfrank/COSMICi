# pinger.py

#------------------------------------------------------------------------
# class NodePinger - A NodePinger is an object that uses a new thread to
#   take on the task of asynchronously "pinging" a given node (via Wi-Fi
#   to its bridged STDIN port) to make sure that it is still alive.  This
#   will (ideally) trigger the node to send a PONG message back to us.

MINUTES_PER_PING = 1    # 1 minute between successive pings sent to each node.

class NodePinger:
    # .node - The node that we're responsible for pinging.
    # .thread - The thread that we're using to ping it.
    def __init__(self, node):
        self.node = node        # Remember what node we're responsible for pinging.
        # Create our thread to run our pingloop.
        self.thread = threading.Thread(target=self.pingloop)
        # Go ahead and start the thread.
        self.thread.start()

    def sendping(self):     # Send a ping to the node's STDIN.
        self.node.auxioServer.send("ping\n")     # Send the node a "ping" command line.

    def pingloop(self):
        logger.debug("Pinger for node %d is waiting 10 seconds to give node a chance to set up its bridges..." % self.node.nodenum)
        time.sleep(10)               # Wait 10 seconds for node to create its bridges.
        logger.debug("Pinger for node %d entering its main ping loop..." % self.node.nodenum)
        while True:
            logger.info("Pinger for node %d about to send ping at %s (+ <1 sec)" % (self.node.nodenum, time.ctime()))
            self.sendping()
            logger.debug("Pinger for node %d is going to sleep for %d minutes..." % (self.node.nodenum, MINUTES_PER_PING))
            time.sleep(60*MINUTES_PER_PING)
        
