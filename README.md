# Onion Routing

A final project for the Gvahim program. this project offers a system that creates anonimizer based on socks5 protocol
(rfc 1928 - https://www.ietf.org/rfc/rfc1928.txt).
The program is based on different nodes and a registry contains name, ip, and secret key of each node.
Registry is HTTP server, allowing register and unregister services.
Each node is a listener which registers itself to registry and listens to a chosen port.

The program works the following way:
The client (browser) connects to the first node via socks5. Once connection is recieved the first node will look up the 
registry for three additional random nodes.
The first node will establish socks with the second node encrypted using second node's key.
The first node will establish socks with the third node using third node's key.
The first node will establish socks with the fourth node using fourth node's key.
Once last connection is established the first node will forward the original socks connection from the client to 
the fourth node encrypted by fourth node's key.
In practice it will be as if browser connected directly to the fourth node via socks, thus creating an anonimizer. 


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

In order to run the project there are some requirments:
```
1) Download and install Python 2.7 (https://www.python.org/download/releases/2.7/)
2) Download this repository and extract the zip.
3) Download and install the latest version of Firefox (https://www.mozilla.org/en-US/firefox/)
4) Change Firefox settings to connect via Socks5 to your local ip and port 1080.
5) Change the address in all configuration files to your ip.
```

### Execution

To execute the project open Command Prompt (or Terminal on Linux):
Reach the parent folder of this project:
```
cd [location of onion_routing]
```
Running Registry and the first node:
```
python -m registry_node [args]
```
Running Node:
```
python -m node_server [args]
```

### Arguments

The node_server requires bind port, so excecution will be:
```
python -m node_server --bind-port 2080
```
Note: Other arguments for both node_server and registry_node are optional, see --help or -h for help.


### Graphical Interface

There is no graphical interface as part of the main program.
In order too enter the GUI in your prefered browser (not Firefox as Firefox should be working with socks5)
type:
```
(your_ip):8080/statistics
```
This will open the main page where statistics about the program may be seen.

Note: Unless registry_node is running GUI won't work as it uses the registry (HTTP server).


## Authors

* **Liron Berger** - *Initial work* - [My Profile](https://github.com/Liron-Berger)

See also the list of [contributors](https://github.com/Liron-Berger/Onion-Routing/graphs/contributors) who participated in this project.


## Acknowledgments

* Thanks to Alon and Sarit for all their support and great teaching!