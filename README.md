# cache-server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built with Nix](https://img.shields.io/badge/Built%20With-Nix-5277C3.svg?logo=nixos&logoColor=white)](https://nixos.org)
[![Compatible with Cachix](https://img.shields.io/badge/Compatible%20with-Cachix-orange.svg)](https://cachix.org)

**A self-hostable, distributed Nix binary cache server with flexible storage strategies**

[Key Features](#-key-features)
[Installation](#-installation)
[Configuration](#%EF%B8%8F-configuration)
[Usage](#%EF%B8%8F-usage)
[Known Limitations](#%EF%B8%8F-known-limitations)
[Contributing](#-contributing)
[License](#-license)
[Acknowledgements](#-acknowledgements)


This project provides a solution for distributed Nix binary cache management, developed as part of the bachelor's thesis _"Distributed Nix Archive Storage"_ at Brno University of Technology, Faculty of Information Technology by Radim Mifka (2025).

----------

## 🚀 Key Features
-   **Distributed Cache Network**  
    Uses [OpenDHT](https://github.com/savoirfairelinux/opendht) for decentralized access to cache servers across multiple nodes.

-   **Cachix-Compatible**  
    Fully supports the Cachix client for seamless binary pushing and fetching.

-   **Flexible Storage Backends**  
    Supports local and S3 storage backends with optional storage _strategies_ for distributing data across multiple backends.

-   **Declarative Configuration**  
    Simple YAML configuration with per-cache settings, supporting multiple cache instances on a single server.


## 🛠 Installation

### Using Nix

The simplest way to build the project is using Nix:

```bash
# Build the project
nix-build

# Run the server
./result/bin/cache-server
```


### Development Environment

To set up a development environment:

```bash
# Enter development shell
nix-shell

# Run using
./server.sh

# Run Static analysis
mypy cache_server_app/main.py
```


## ⚙️ Configuration
The configuration file is located at:
`$XDG_CONFIG_HOME/cache-server/config.yaml`

### 📁 Server Configuration

```yaml
server:
  database: "node.db"              # SQLite database file
  hostname: "0.0.0.0"               # Bind address
  standalone: false                 # Operate in standalone mode (no DHT)
  dht-port: 4222                    # Port for DHT communication
  dht-bootstrap-host: "other-node"  # Bootstrap node for DHT
  dht-bootstrap-port: 4223          # Bootstrap node port
  server-port: 5001                 # HTTP API port
  deploy-port: 5002                 # Deployment API port
  key: "your-secret-key-here"       # Authentication key
  default-retention: 4              # Default retention period (days)
  default-port: 8080                # Default HTTP port
```


### 📦 Cache Instances
Define multiple cache instances with individual settings:

```yaml
caches:
  - name: "main"                   # Cache name
    retention: 7                   # Override default retention (days)
    port: 8081                     # Override default port
    storage-strategy: "split"      # Storage strategy (see below)
    storages:
      - name: "local-fast"
        type: "local"
        root: "binary-caches"      # Local path
        split: 40                  # Percentage for split strategy
      - name: "external-usb"
        type: "local"
        root: "/Volumes/USB/binary-caches"
        split: 60
```


### 🗄️ Storage Backends
**Required Fields**:
- **name** - name of the storage
- **type** - type of the storage
- **root** - root path for storage

| Type  | Extra Required Fields                                      |
| ----- | ---------------------------------------------------------- |
| local |                                                            |
| s3    | s3_bucket, s3_region, s3_access_key, s3_secret_key |


Example S3 configuration:

```yaml
- name: "remote"
  type: "s3"
  root: "binary-caches"        # Folder within bucket
  s3_bucket: "cache-1"
  s3_region: "eu-central-1"
  s3_access_key: "access-key"
  s3_secret_key: "secret-key"
```

### 🔁 Storage Strategy

> ⚠️ Strategies only apply if more than one storage backend is defined.

Configure how data is distributed across storage backends:
| Strategy      | Description                                                         | Config Requirements           |
| ------------- | ------------------------------------------------------------------- | ----------------------------- |
| round-robin | Cycles through storages one by one for each new file.               | No extra fields               |
| in-order    | Uses storages in listed order until full before moving to the next. | No extra fields               |
| split       | Distributes files based on a percentage split between storages.     | split field on each storage |
| least-used  | Dynamically picks the storage with the least usage.                 | No extra fields               |

Example with split strategy:

```yaml
storage-strategy: "split"
storages:
  - name: "storage-1"
    type: "local"
    root: "/fast"
    split: 70
  - name: "storage-2"
    type: "s3"
    root: "binary-caches"
    s3_bucket: "backup"
    s3_region: "eu-central-1"
    s3_access_key: "key"
    s3_secret_key: "secret"
    split: 30
```

### 🧩 Workspaces and Agents
To enable integration with Cachix Deploy, you can define `workspaces` and `agents` in the configuration:
```yaml
workspaces:
  - name: "workspace1"
    cache: "first"

agents:
  - name: "agent1"
    workspace: "workspace1"
```
These settings allow the server to support deployments using Cachix agents and workspaces. For more information on how these components work and how to run agents, see the [Cachix Deploy documentation](https://docs.cachix.org/deploy/).

## ▶️ Usage

### Starting the Server

```bash
# Starting the server
./result/bin/cache-server
```

### Pushing Binaries

Use the Cachix client to push derivations:

```bash
# Push a specific derivation
cachix push your-cache-name /nix/store/hash-name

# Push closure of a derivation
nix-store -qR $(which your-program) | cachix push your-cache-name
```


See [Cachix documentation](https://docs.cachix.org/) for more details.

## ⚠️ Known Limitations

- **Legacy Components**: Features like workspaces and agents are retained from previous version but remain untested and may not function reliably.
- **Lack of Automated Testing**: Due to the complexity of the distributed setup, the project currently lacks comprehensive automated tests.
- **Monitoring**: No unified monitoring or logging system is currently implemented.
- **Deprecated CLI Tool**: A CLI is no longer maintained, as its functionality has been integrated or made obsolete by configuration-driven design.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Marek Križan, author of the previous version of this project, which served as a foundation for this work
- Marek Rychlý, thesis supervisor, for guidance and support throughout the project
- [Attic](https://github.com/zhaofengli/attic) implementation, which provided inspiration
- [OpenDHT](https://github.com/savoirfairelinux/opendht) for the distributed networking capabilities
