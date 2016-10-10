# netTelD
Daemon which implements netTel as described in : https://docs.google.com/presentation/d/1uqVGDOPo5-3Nh-RG8vp5PKpKqlQo2ZMNAimxqwf6bs0/edit#slide=id.g1781e444bf_0_10


### Usage:
* start: systemctl stop netTelD.service
* stop: systemctl stop netTelD.service
* status: systemctl status netTelD.service
* alternativley you can start it directly as a daemon from the executable:
  * start: ./netTel.py start
  * etc.

### Installation
See the bottom of the requirements document: https://docs.google.com/document/d/1ToY17b2JHOeKtQSarso97KRYrph7KALUVVRSy1JyniQ/edit?usp=sharing  (under construction) 

### Log
The log can be found here: /var/log/netTel/netTel.log

### Monitoring
See how the output of netTel performs in comparison to its two inputs: https://mig-graphite.cern.ch/grafana/dashboard/file/client.json?var-cluster=netmon&var-client=perfsonar-raw-histogram-owdelay&var-client=perfsonar-raw-packet-loss-rate&var-client=telemetry-perfsonar&var-top=8&from=now-3h&to=now
