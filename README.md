# CloudLab/Emulab JSON Profile (Phase-1)

This profile consumes a single JSON specification to create a CloudLab/Emulab experiment.

## How It Works

- Pass your experiment specification as the `spec_json` parameter in the CloudLab/Emulab portal.
- The script parses the JSON, validates it, and outputs a corresponding RSpec.

## Supported Node Types

### rawpc

Represents a physical machine (can be exclusive).

| Field           | Type   | Required | Notes                                   |
| --------------- | ------ | -------- | --------------------------------------- |
| `name`          | string | yes      | Unique node name.                       |
| `hardware_type` | string | no       | Requested hardware type (e.g., d430).   |
| `exclusive`     | bool   | no       | If true, request a dedicated host.      |
| `disk_image`    | string | no       | URN or alias of desired image.          |
| `aggregate`     | string | no       | Component Manager URN.                  |
| `routable_ip`   | bool   | no       | Request a routable control IP.          |
| `blockstores`   | array  | no       | List of blockstore objects (see below). |

### xenvm

Represents a Xen virtual machine. Can optionally be placed on a rawpc.

| Field            | Type   | Required | Notes                              |
| ---------------- | ------ | -------- | ---------------------------------- |
| `name`           | string | yes      | Unique node name.                  |
| `cores`          | int    | no       | Number of cores.                   |
| `ram`            | int    | no       | RAM in MB.                         |
| `disk`           | int    | no       | Disk size in GB.                   |
| `instantiate_on` | string | no       | Name of rawpc to pin VM placement. |
| `disk_image`     | string | no       | URN or alias of desired image.     |
| `aggregate`      | string | no       | Component Manager URN.             |
| `routable_ip`    | bool   | no       | Request a routable control IP.     |
| `blockstores`    | array  | no       | List of blockstore objects.        |

### Blockstore Object

| Field   | Type   | Required | Notes                      |
| ------- | ------ | -------- | -------------------------- |
| `name`  | string | yes      | Identifier for blockstore. |
| `mount` | string | no       | Mount path inside node.    |
| `size`  | int    | yes      | Size in GB.                |

## Supported Link Types

| Kind           | Description                                  |
| -------------- | -------------------------------------------- |
| `link`         | Point-to-point Ethernet link (2 interfaces). |
| `lan`          | Multi-access LAN (≥2 interfaces).            |
| `bridged_link` | Link with bandwidth/latency/PLR properties.  |

Link object fields:

| Field        | Type   | Required | Notes                      |
| ------------ | ------ | -------- | -------------------------- |
| `name`       | string | yes      | Link name.                 |
| `interfaces` | array  | yes      | Array of `{node, ifname}`. |
| `bandwidth`  | int    | no       | Mbps (bridged_link only).  |
| `latency`    | int    | no       | ms (bridged_link only).    |
| `plr`        | float  | no       | Packet loss rate (0..1).   |

### Interface Object

| Field    | Type   | Required | Notes                                |
| -------- | ------ | -------- | ------------------------------------ |
| `node`   | string | yes      | Node name this interface belongs to. |
| `ifname` | string | no       | Custom interface name.               |

## Example JSON

```json
{
  "nodes": [
    {
      "kind": "rawpc",
      "name": "host1",
      "hardware_type": "d430",
      "exclusive": true,
      "blockstores": [{ "name": "bs1", "mount": "/data1", "size": 20 }]
    },
    {
      "kind": "xenvm",
      "name": "vm1",
      "cores": 2,
      "ram": 4096,
      "disk": 20,
      "instantiate_on": "host1"
    }
  ],
  "links": [
    {
      "kind": "lan",
      "name": "lan0",
      "interfaces": [{ "node": "host1" }, { "node": "vm1" }]
    }
  ]
}
```
