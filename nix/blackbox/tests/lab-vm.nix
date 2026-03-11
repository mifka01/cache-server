{ pkgs, cacheServerPkg }:

let
  lib = pkgs.lib;

  mkServer = index: {
    name = "server${toString index}";
    value = import ../mk-server-node.nix {
      inherit pkgs cacheServerPkg;
      nodeName = "server${toString index}";
      dhtPort = 4221 + index;
      serverPort = 5000 + index;
      deployPort = 6000 + index;
      cachePort = 7000 + index;
      bootstrapHost = "server1";
      bootstrapDhtPort = 4222;
      cacheName = "main";
    };
  };

  mkClient = index: {
    name = "client${toString index}";
    value = import ../mk-client-node.nix {
      inherit pkgs;
      serverHost = "server1";
      serverPort = 5001;
      cacheName = "main";
      nodeName = "client${toString index}";
      uploadHostIp = "192.168.1.2";
    };
  };

  serverNodes = lib.listToAttrs (map mkServer (lib.range 1 5));
  clientNodes = lib.listToAttrs (map mkClient (lib.range 1 5));
in
pkgs.testers.runNixOSTest {
  name = "cache-server-lab-vm";
  nodes = serverNodes // clientNodes;
  testScript = "pass";
}
