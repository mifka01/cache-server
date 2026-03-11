{ pkgs, cacheServerPkg }:

{
  serverSpecs ? [
    {
      name = "servera";
      dhtPort = 4222;
      serverPort = 5001;
      deployPort = 6001;
      cachePort = 7001;
      bootstrapHost = "servera";
      bootstrapDhtPort = 4222;
    }
    {
      name = "serverb";
      dhtPort = 4223;
      serverPort = 5002;
      deployPort = 6002;
      cachePort = 7002;
      bootstrapHost = "servera";
      bootstrapDhtPort = 4222;
    }
  ],
  clientName ? "client",
  clientServerHost ? "servera",
  clientServerPort ? 5001,
  cacheName ? "main",
  clientArgs ? { },
}:
let
  lib = pkgs.lib;
  serverNodes = lib.listToAttrs (map
    (spec: {
      name = spec.name;
      value = import ../mk-server-node.nix {
        inherit pkgs cacheServerPkg;
        nodeName = spec.name;
        inherit (spec)
          bootstrapHost
          dhtPort
          bootstrapDhtPort
          serverPort
          deployPort
          cachePort;
        inherit cacheName;
      };
    })
    serverSpecs);

  clientNode = {
    ${clientName} = import ../mk-client-node.nix ({
      inherit pkgs;
      serverHost = clientServerHost;
      serverPort = clientServerPort;
      inherit cacheName;
    } // clientArgs);
  };
in
{
  nodes = serverNodes // clientNode;
  inherit serverSpecs clientName cacheName;
}
