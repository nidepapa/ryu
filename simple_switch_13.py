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


from ryu.lib.packet import ether_types
from ryu.lib.packet import *
from ryu.lib.packet import tcp
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.topology.api import get_switch, get_link
from ryu.topology import event

import networkx as nx

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)

        self.topology_api_app = self
        self.mac_to_port = {}
        self.network = nx.DiGraph()
        self.nodes = {}
        self.links = {}
        self.no_of_nodes = 0
        self.no_of_links = 0
        self.i = 0
        self.anycast_ip = '10.10.10.10'
        #anycast controller dict
        self.hw = {'h3':['00:00:00:00:00:03', '10.0.0.3'],
                   'h4':['00:00:00:00:00:04', '10.0.0.4'],
                   }

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
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

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        print "\n-----------get_topology_data"

        switch_list = get_switch(self.topology_api_app, None)
        switches = [switch.dp.id for switch in switch_list]
        self.network.add_nodes_from(switches)

        links_list = get_link(self.topology_api_app, None)
        links = [(link.src.dpid, link.dst.dpid, {'port': link.src.port_no}) for link in links_list]
        self.network.add_edges_from(links)
        links = [(link.dst.dpid, link.src.dpid, {'port': link.dst.port_no}) for link in links_list]
        self.network.add_edges_from(links)
        print "-----------List of links"
        print self.network.edges()
    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        if  pkt.get_protocol(arp.arp):
            self.logger.info("Send ARP_REPLY")
        self.logger.info("--------------------")
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,buffer_id=ofproto.OFP_NO_BUFFER,in_port=ofproto.OFPP_CONTROLLER,actions=actions,data=data)
        datapath.send_msg(out)

    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp):
        if pkt_arp.opcode != arp.ARP_REQUEST:
            return
        print "-----------choose controller"

        path_h3 = [1,2,3]#nx.shortest_path(self.network, pkt_ethernet.src, self.hw['h3'][0])
        path_h4 = [1,2,3]#nx.shortest_path(self.network, pkt_ethernet.src, self.hw['h4'][0])
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
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        pkt_arp = pkt.get_protocol(arp.arp)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)


        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        if src not in self.network:
            self.network.add_node(src)
            self.network.add_edge(dpid, src, port=in_port)
            self.network.add_edge(src, dpid)
        if dst in self.network:
            path = nx.shortest_path(self.network, src, dst)
            print "dpid=", dpid

            next = path[path.index(dpid) + 1]
            out_port = self.network[dpid][next]['port']
        else:
            out_port = ofproto.OFPP_FLOOD
        if pkt_arp:
            if pkt_arp.dst_ip == self.anycast_ip:
                # do something to anycast
                self._handle_arp(datapath, in_port, eth, pkt_arp)

        if pkt.get_protocol(tcp.tcp):
            print('TCP!')
            if pkt_ipv4.dst == self.anycast_ip:
                self.logger.info("its anycast packet!")
                match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=self.anycast_ip)
                if eth.dst == self.hw['h3'][0]:
                    set_field = parser.OFPActionSetField(ipv4_dst=self.hw['h3'][1])
                elif eth.dst == self.hw['h4'][0]:
                    set_field = parser.OFPActionSetField(ipv4_dst=self.hw['h4'][1])
                actions = [set_field, parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 100, match, actions, )
                self.logger.info("set flow!")
                return
                # ingress
            if pkt_ipv4.src == self.hw['h3'][1]:
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=self.hw['h3'][1])
                set_field = parser.OFPActionSetField(ipv4_src=self.anycast_ip)
                actions = [set_field, parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 100, match, actions, )
                self.logger.info("set flow!")
                return
            if pkt_ipv4.src == self.hw['h4'][1]:
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=self.hw['h4'][1])
                set_field = parser.OFPActionSetField(ipv4_src=self.anycast_ip)
                actions = [set_field, parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 100, match, actions, )
                self.logger.info("set flow!")
                return
            # install a flow to avoid packet_in next time











