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

    net = Mininet( controller=RemoteController, switch=OVSSwitch )

    info("*** Creating (reference) controllers\n")
    #anycast-controller
    ca = net.addController('ca', controller=RemoteController, ip='10.10.10.10')
    c1 = net.addController('c1', controller=RemoteController, ip='10.0.0.3', port=6653)
    c2 = net.addController('c2', controller=RemoteController, ip='10.0.0.4', port=6653)
    #control-controller
    c0 = net.addController('c0', controller=RemoteController, ip='192.168.142.132', port=6653)

    info( "*** Creating switches\n" )
    s1 = net.addSwitch( 's1',  )
    s2 = net.addSwitch( 's2',  )
    s3 = net.addSwitch( 's3',  )
    s4 = net.addSwitch( 's4',  )
    s5 = net.addSwitch( 's5',  )

    #for i in range(10,85):
     #   name = 's' + str(i)
      #  locals()['s' + str(i)] = net.addSwitch( name  )
       # net.addLink( locals()['s' + str(i)], s2)





    info( "*** Creating hosts\n" )

    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4', mac='00:00:00:00:00:04')
    h5 = net.addHost('h5', ip='10.0.0.5', mac='00:00:00:00:00:05')
    h6 = net.addHost('h6', ip='10.0.0.6', mac='00:00:00:00:00:06')

    info( "*** Creating links\n" )
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s3)
    net.addLink(h4, s4)
    net.addLink(h6, s4)
    net.addLink(h5, s5)
#Link between switchs
    net.addLink( s1, s2 )
    net.addLink( s3, s2 )
    net.addLink( s4, s2 )
    net.addLink( s5, s2 )
    net.addLink( s5, s1 )



    info( "*** Starting network\n" )
    net.build()
    c0.start()
    c1.start()
    c2.start()

    # Start control-controller,through TCP ,connection built
    s1.start([c0,c2])
    s2.start([c0,])
    s3.start([c0])
    s4.start([c0])
    s5.start([c0,])
    # Start anycast-controller
    #for i in range(10, 85):
     #   locals()['s' + str(i)].start([c0,ca])





    #set ip to switch
    s1.cmd('ifconfig s1 inet 10.0.0.11')
    s2.cmd('ifconfig s2 inet 10.0.0.12')
    s3.cmd('ifconfig s3 inet 10.0.0.13')
    s4.cmd('ifconfig s4 inet 10.0.0.14')
    s5.cmd('ifconfig s5 inet 10.0.0.15')



    #info( "*** Testing network\n" )
    #net.pingAll()

    info( "*** Running CLI\n" )
    CLI( net )

    info( "*** Stopping network\n" )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )  # for CLI output
    multiControllerNet()

