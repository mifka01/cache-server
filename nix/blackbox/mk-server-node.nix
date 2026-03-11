{
  pkgs,
  cacheServerPkg,
  nodeName,
  bootstrapHost,
  dhtPort,
  bootstrapDhtPort,
  serverPort,
  deployPort,
  cacheName ? "main",
  cachePort ? 7001,
  cacheAccess ? "public",
  key ? "test-key",
  retention ? 7,
}: {
  lib,
  ...
}: {
  networking.hostName = nodeName;
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 80 serverPort deployPort cachePort dhtPort bootstrapDhtPort ];
  networking.firewall.allowedUDPPorts = [ dhtPort bootstrapDhtPort ];

  services.openssh.enable = true;
  services.openssh.settings = {
    PermitRootLogin = "yes";
    PasswordAuthentication = true;
  };
  users.users.root.initialHashedPassword = lib.mkForce null;
  users.users.root.hashedPasswordFile = lib.mkForce null;
  users.users.root.initialPassword = "root";

  environment.systemPackages = [
    cacheServerPkg
    pkgs.curl
    pkgs.jq
    pkgs.sqlite
    pkgs.socat
  ];

  systemd.services.cache-server = {
    description = "cache-server";
    wantedBy = [ "multi-user.target" ];
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];

    serviceConfig = {
      Type = "simple";
      Restart = "on-failure";
      Environment = [ "XDG_CONFIG_HOME=/var/lib" ];
      ExecStart = "${cacheServerPkg}/bin/cache-server";
    };

    preStart = ''
      mkdir -p /var/lib/cache-server
      mkdir -p /var/lib/cache-server/data
      mkdir -p /var/lib/cache-server/caches

      cat > /var/lib/cache-server/config.yaml <<EOF
      server:
        database: "/var/lib/cache-server/data/${nodeName}.db"
        hostname: "0.0.0.0"
        standalone: false
        dht-port: ${toString dhtPort}
        dht-bootstrap-host: "${bootstrapHost}"
        dht-bootstrap-port: ${toString bootstrapDhtPort}
        server-port: ${toString serverPort}
        deploy-port: ${toString deployPort}
        key: "${key}"

      caches:
        - name: "${cacheName}"
          port: ${toString cachePort}
          access: "${cacheAccess}"
          retention: ${toString retention}
          storage-strategy: "in-order"
          storages:
            - name: "local"
              type: "local"
              root: "/var/lib/cache-server/caches"

      workspaces: []
      agents: []
      EOF
    '';
  };

  # Cachix expects upload hosts from cache URL on port 80.
  # Proxy :80 to the cache endpoint port used by this node.
  systemd.services.cache-http-proxy = {
    description = "cache-server port 80 proxy";
    wantedBy = [ "multi-user.target" ];
    wants = [ "network-online.target" "cache-server.service" ];
    after = [ "network-online.target" "cache-server.service" ];

    serviceConfig = {
      Type = "simple";
      Restart = "always";
      RestartSec = "1s";
      ExecStart = "${pkgs.socat}/bin/socat TCP-LISTEN:80,reuseaddr,fork TCP:127.0.0.1:${toString cachePort}";
    };
  };
}
