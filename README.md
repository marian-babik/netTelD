# netTelD
Daemon which implements netTel as described in : https://docs.google.com/presentation/d/1uqVGDOPo5-3Nh-RG8vp5PKpKqlQo2ZMNAimxqwf6bs0/edit#slide=id.g1781e444bf_0_10

Currently and without optimization the script is able to process about 19~23
messages per second on a low end system. That is about twice as much as the message bus (ActiveMQ)
currently feeds as raw data.
On our production system the script is able to processes about 30~35 messages per second. 

### Usage:
* start: systemctl stop netTelD.service
* stop: systemctl stop netTelD.service
* status: systemctl status netTelD.service
* alternatively you can start it directly as a daemon from the executable:
  * start: ./netTel.py start
  * etc.

### Installation
See the bottom of the requirements document: https://docs.google.com/document/d/1ToY17b2JHOeKtQSarso97KRYrph7KALUVVRSy1JyniQ/edit?usp=sharing  (under construction) 

### Log
The log can be found here: /var/log/netTel/netTel.log

### Monitoring
See how the output of netTel performs in comparison to its two inputs: https://mig-graphite.cern.ch/grafana/dashboard/file/client.json?var-cluster=netmon&var-client=perfsonar-raw-histogram-owdelay&var-client=perfsonar-raw-packet-loss-rate&var-client=telemetry-perfsonar&var-top=8&from=now-3h&to=now

### Machine requirements
* Memory footprint With all (~5600) connections fully buffered: ~ 270 MB
* CPU usage: 1 CPU, with usage spikes up to ~50%
* Disk: Maximum of about 25 MB