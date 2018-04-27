#!/usr/bin/python

"""
This example creates a multi-controller network from semi-scratch by
using the net.add*() API and manually starting the switches and controllers.
This is the "mid-level" API, which is an alternative to the "high-level"
Topo() API which supports parametrized topology classes.
Note that one could also create a custom switch class and pass it into
the Mininet() constructor.
"""


from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def multiControllerNet():
    "Create a network from semi-scratch with multiple controllers."

    net = Mininet( controller=Controller, switch=OVSSwitch )

    info( "*** Creating (reference) controllers\n" )
    c1 = net.addController( 'c1', port=6633 )
    c2 = net.addController( 'c2', port=6634 )
    c0 = net.addController( RemoteController( 'c0', ip='192.168.142.135', port=6653 )  )


    info( "*** Creating switches\n" )
    s1 = net.addSwitch( 's1' )
    s2 = net.addSwitch( 's2' )
    s3 = net.addSwitch( 's3' )
    s4 = net.addSwitch( 's4' )


    info( "*** Creating hosts\n" )
    hosts1 = [ net.addHost( 'h%d' % n ) for n in ( 3, 4 ) ]
    #hosts2 = [ net.addHost( 'h%d' % n ) for n in ( 5, 6 ) ]

    info( "*** Creating links\n" )
    for h in hosts1:
        net.addLink( s1, h )
   # for h in hosts2:
    #    net.addLink( s2, h )
    net.addLink( s1, s2 )
    net.addLink( s3, s2 )
    net.addLink( s4, s2 )

    info( "*** Starting network\n" )
    net.build()
    c0.start()
    c1.start()
    c2.start()
    s1.start( [ c0 ] )
    s2.start( [ c0 ] )
    s3.start( [ c1, c0 ] )
    s4.start( [ c2, c0 ] )
   



    info( "*** Testing network\n" )
    net.pingAll()

    info( "*** Running CLI\n" )
    CLI( net )

    info( "*** Stopping network\n" )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )  # for CLI output
    multiControllerNet()
