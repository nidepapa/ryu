# coding:utf-8
# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import *
from ryu.lib.packet import tcp
from ryu.lib import mac
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches

import networkx as nx



class ProjectController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        self.topology_api_app = self
        self.net = nx.DiGraph()
        self.nodes = {}
        self.links = {}
        self.no_of_nodes = 0
        self.no_of_links = 0
        self.i = 0
        self.anycast_ip = '10.10.10.10'

        # anycast controller dict:
        self.hw = {'h3':['00:00:00:00:00:03', '10.0.0.3'],
                   'h4':['00:00:00:00:00:04', '10.0.0.4'],
                   }

        print "**********ProjectController __init__"

    # not used :
    def printG(self):
        G = self.net
        print "G"
        print "nodes", G.nodes()  # 输出全部的节点： [1, 2, 3]
        print "edges", G.edges()  # 输出全部的边：[(2, 3)]
        print "number_of_edges", G.number_of_edges()  # 输出边的数量：1
        for e in G.edges():
            print G.get_edge_data(e[0], e[1])

    # not used (Handy function that lists all attributes in the given object)
    def ls(self, obj):
        print("\n".join([x for x in dir(obj) if x[0] != "_"]))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        print "\n-----------switch_features_handler is called"

        msg = ev.msg
        print 'OFPSwitchFeatures received: datapath_id=0x%016x n_buffers=%d n_tables=%d auxiliary_id=%d capabilities=0x%08x' % (
            msg.datapath_id, msg.n_buffers, msg.n_tables, msg.auxiliary_id, msg.capabilities)

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0, priority=0, instructions=inst)
        datapath.send_msg(mod)
        print "switch_features_handler is over"

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        print "\n-----------get_topology_data"

        switch_list = get_switch(self.topology_api_app, None)
        switches = [switch.dp.id for switch in switch_list]
        self.net.add_nodes_from(switches)

        print "-----------List of switches"
        for switch in switch_list:

            print switch
        # -----------------------------
        links_list = get_link(self.topology_api_app, None)
        links = [(link.src.dpid, link.dst.dpid, {'port': link.src.port_no}) for link in links_list]
        self.net.add_edges_from(links)
        #reverse
        links = [(link.dst.dpid, link.src.dpid, {'port': link.dst.port_no}) for link in links_list]
        self.net.add_edges_from(links)

        print "-----------List of links"
        print self.net.edges()


    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    # only used in method _handle_arp
    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        if pkt.get_protocol(arp.arp):
            self.logger.info("Send ARP_REPLY")
        self.logger.info("--------------------")
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions, data=data)
        datapath.send_msg(out)

    # only handle anycast arp
    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp):
        dpid = datapath.id
        if pkt_arp.opcode != arp.ARP_REQUEST:
            return
        print "-----------choose controller"
        #3 and 4 are the dpid of the c1 and c2
        path_h3 = nx.shortest_path(self.net, dpid, 3)
        path_h4 = nx.shortest_path(self.net, dpid, 4)
        pkt = packet.Packet()
        # choose a controller between h3 and h4
        if len(path_h3) > len(path_h4):
            pkt.add_protocol(
                ethernet.ethernet(ethertype=pkt_ethernet.ethertype, dst=pkt_ethernet.src, src=self.hw['h4'][0]))
            pkt.add_protocol(
                arp.arp(opcode=arp.ARP_REPLY, src_mac=self.hw['h4'][0], src_ip=pkt_arp.dst_ip, dst_mac=pkt_arp.src_mac,
                        dst_ip=pkt_arp.src_ip))
        else:
            pkt.add_protocol(
                ethernet.ethernet(ethertype=pkt_ethernet.ethertype, dst=pkt_ethernet.src, src=self.hw['h3'][0]))
            pkt.add_protocol(
                arp.arp(opcode=arp.ARP_REPLY, src_mac=self.hw['h3'][0], src_ip=pkt_arp.dst_ip, dst_mac=pkt_arp.src_mac,
                        dst_ip=pkt_arp.src_ip))

        self.logger.info("Receive ARP_REQUEST,request IP is %s", pkt_arp.dst_ip)
        self._send_packet(datapath, port, pkt)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # print "**********_packet_in_handler"
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocol(ethernet.ethernet)
        pkt_arp = pkt.get_protocol(arp.arp)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        if pkt.get_protocol(icmp.icmp):
            # ignore icmp
            return

        # handle anycast arp specificly
        if pkt_arp:
            if pkt_arp.dst_ip == self.anycast_ip:
                # do something to anycast
                self._handle_arp(datapath, in_port, eth, pkt_arp)
                return

        # handle tcp :
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})


        if src not in self.net:
            self.net.add_node(src)
            self.net.add_edge(dpid, src, port=in_port)
            self.net.add_edge(src, dpid)
        if dst in self.net:

            # using shortest_path to find the path
            path = nx.shortest_path(self.net, src, dst)

            print "dpid=", dpid
            print "length=", nx.shortest_path_length(self.net, src, dst)

            # make sure the dpid is in the path or do not set flow
            if dpid in path:
               next = path[path.index(dpid) + 1]
               out_port = self.net[dpid][next]['port']
            else:
                out_port = ofproto.OFPP_NORMAL
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time and avoid storm
        if out_port != ofproto.OFPP_FLOOD :
            # set flow according to different match at specific switch (dpid)
            if pkt.get_protocol(tcp.tcp):
                print('TCP!')
                # the first SYN:
                if pkt_ipv4.dst == self.anycast_ip and dpid ==3:
                    self.logger.info("its anycast packet!")
                    match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=self.anycast_ip)
                    if eth.dst == self.hw['h3'][0]:
                        set_field = parser.OFPActionSetField(ipv4_dst=self.hw['h3'][1])
                    elif eth.dst == self.hw['h4'][0]:
                        set_field = parser.OFPActionSetField(ipv4_dst=self.hw['h4'][1])
                    actions = [set_field, parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 100, match, actions, )
                    self.logger.info(" s3 set flow!")
                    return



                    # ingress
                # the second SYN,ACK
                if pkt_ipv4.src == self.hw['h3'][1] and dpid ==3:
                    match = parser.OFPMatch(eth_type=0x0800, ipv4_src=self.hw['h3'][1])
                    set_field = parser.OFPActionSetField(ipv4_src=self.anycast_ip)
                    actions = [set_field, parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 100, match, actions, )
                    self.logger.info("s3 set flow!")
                    return
                if pkt_ipv4.src == self.hw['h4'][1] and dpid ==4:
                    match = parser.OFPMatch(eth_type=0x0800, ipv4_src=self.hw['h4'][1])
                    set_field = parser.OFPActionSetField(ipv4_src=self.anycast_ip)
                    actions = [set_field, parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 100, match, actions, )
                    self.logger.info(" s3 set flow!")
                    return
                    # install a flow to avoid packet_in next time
                # at s2 must set flow to pass pkt to the right port
                if pkt_ipv4.src == self.anycast_ip and dpid == 2:
                    match = parser.OFPMatch(eth_type=0x0800, ipv4_src=self.anycast_ip, ipv4_dst=pkt_ipv4.dst)
                    actions = [parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 100, match, actions, )
                    self.logger.info(" s2 set flow!")

            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions)
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions)
        datapath.send_msg(out)