# ryu
apps used in the sdn based on ryu
本次试验的的内容是使用ryu调度控制器来进行anycast的链接，也就是为任意一台网络中的交换机选择最好的控制器。

STEP1
用python运行mynet文件搭建好RYU+Mininet的网络结构，包含以下组件：
c0 调度控制器的主控制器master (唯一的不同网段)
c1，c2收c0的调度的slave
s1~s5, 交换机直接与c1或c2相连
h1~h6与交换机相连。

STEP2
环境搭建好后，就要首先确定网络拓扑。本次实验的拓扑图如下
















<!--
 /* Font Definitions */
@font-face
	{font-family:宋体;
	mso-font-charset:134;
	mso-generic-font-family:auto;
	mso-font-pitch:variable;
	mso-font-signature:3 680460288 22 0 262145 0;}
@font-face
	{font-family:"Cambria Math";
	panose-1:2 4 5 3 5 4 6 3 2 4;
	mso-font-charset:0;
	mso-generic-font-family:roman;
	mso-font-pitch:variable;
	mso-font-signature:-536870145 1107305727 0 0 415 0;}
 /* Style Definitions */
p.MsoNormal, li.MsoNormal, div.MsoNormal
	{mso-style-unhide:no;
	mso-style-qformat:yes;
	mso-style-parent:"";
	margin:0cm;
	margin-bottom:.0001pt;
	mso-pagination:widow-orphan;
	font-size:12.0pt;
	font-family:"Times New Roman",serif;
	mso-fareast-font-family:宋体;}
.MsoChpDefault
	{mso-style-type:export-only;
	mso-default-props:yes;
	font-size:10.0pt;
	mso-ansi-font-size:10.0pt;
	mso-bidi-font-size:10.0pt;
	mso-fareast-font-family:宋体;}
@page WordSection1
	{size:612.0pt 792.0pt;
	margin:72.0pt 72.0pt 72.0pt 72.0pt;
	mso-header-margin:36.0pt;
	mso-footer-margin:36.0pt;
	mso-paper-source:0;}
div.WordSection1
	{page:WordSection1;}
-->















各个控制器和交换机的角色都已经标明。接下来目标就是让s1来请求控制器，c0要可以处理这样的请求并且分配c1或者c2给s1.

STEP3
对于c0要编写RYU应用，要求可以进行ARP代理，并且运行最小路径算法分配最近的控制器给交换机，程序的详细代码在文件shortest-path.py 文件中。打开RYU运行这个文件即可。

STEP4
最后一步就是在mininet中建立上文中的网络拓扑，并且打开控制器c1 c2，并且让主机h1开始ping主机h5，随后c1或者c2中会出现包的信息，此时说明控制器已经分配成功。打开wireshark也可以看到包传递的信息。
