# cache-server - server application compatible with the Cachix client
🚧 **Work in Progress** 🚧

## Introduction

This repository contains the source code of a server application compatible with the Cachix command line client. This application was developed as a part of the bachelor's thesis Remote Distributed Software Deployment in NixOS Systems (Brno University of Technology, Faculty of Information Technology).

Author: Marek Križan

Year: 2024

## Installation

### Install cache-server

To install the cache server run:
```console
git clone https://github.com/xkriza08/cache-server.git
cd cache-server/
nix-build
```

### Configuration

To use the cache-server application it is needed to create `~/.cache-server.conf` configuration file.

For reference use the file `cache-server/config/cache-server.conf` or the example below:
```
[cache-server]
hostname = cache-server
cache-dir = binary-caches
server-port = 12345
database = dbfile.db
deploy-port = 54321
key = secret
```

- **hostname** - Hostname of the cache-server. This hostname should be used by the Cachix command line client to access the cache-server.
- **cache-dir** - Directory in which NAR files will be stored.
- **server-port** - Port, on which the cache-server will listen for HTTP requests.
- **database** - SQLite database file.
- **deploy-port** - Port, on which the cache-server will listen for WebSocket connections.
- **key** - String, that will be used as a secret for JWT authentication tokens

### Additional setup

To forward request to specified ports it is reccomended to set up nginx with the following configuration (for NixOS):

```
services.nginx = {
  enable = true;
  virtualHosts = {
    "<hostname>" = {
      enableACME = false;
      locations."/ws" = {
        proxyPass = "http://localhost:<deploy-port>";
        proxyWebsockets = true;
      };
      locations."/api/v1/deploy/log/" = {
        proxyPass = "http://localhost:<deploy-port>";
        proxyWebsockets = true;
      };
      locations."/" = {
        proxyPass = "http://localhost:<server-port>";
      };
    };
    clientMaxBodySize = "0";
  };
};
```

## Usage

### server side

```console
usage: cache-server [-h] {listen,hidden-start,stop,cache,agent,workspace,store-path} ...

Cache server options

positional arguments:
  {listen,hidden-start,stop,cache,agent,workspace,store-path}
    listen              Start cache server
    stop                Stop cache server
    cache               Manage caches
    agent               Manage deployment agents
    workspace           Manage deployment workspaces
    store-path          Manage store paths

options:
  -h, --help            show this help message and exit
```

#### listen/stop

The cache-server can be started using:

```console
cache-server listen
```

The cache-server can be stopped using:
```console
cache-server stop
```

#### Setting up a binary cache

To create a binary cache run:

```console
cache-server cache create <name> <port>
```

To make the binary cache listen on the specified port run:
```console
cache-server cache start <name>
```

To forward HTTP requests to binary caches add the following nginx configuration for each binary cache:
```
services.nginx = {
  enable = true;
  virtualHosts = {
    "<cache-name>.<hostname>" = {
      enableACME = false;
      locations."/" = {
        proxyPass = "http://localhost:<cache-port>";
      };
    };
  };
};
```

To access information about binary cache (for example authentication token) run:
```console
cache-server cache info <name>
```

#### Setting up deployment agents

To create deployment workspace run:
```console
cache-server workspace create <name> <cache-name>
```

To add agent to workspace run:

```console
cache-server agent add <name> <workspace-name>
```

To access information about workspace (including deployment activation token) run:
```console
cache-server workspace info <name>
```

To access information about agent (including agent token) run:
```console
cache-server agent info <name>
```

### client side

To use cache-server with the Cachix client run:

```
cachix config set hostname http://<hostname>
```
