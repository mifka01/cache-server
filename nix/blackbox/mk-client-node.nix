{
  pkgs,
  serverHost,
  serverPort,
  cacheName,
  nodeName ? "client",
  testSource ? null,
  uploadHostAlias ? "${cacheName}.0.0.0.0",
  uploadHostIp ? "192.168.1.2",
  cacheAuthToken ? "",
  agentToken ? "",
  activateToken ? "",
}: let
  setupScript = pkgs.writeShellScriptBin "cache-test-client-setup" ''
    set -euo pipefail
    export PATH="${pkgs.nix}/bin:${pkgs.coreutils}/bin:${pkgs.gawk}/bin:${pkgs.curl}/bin:${pkgs.cachix}/bin:$PATH"

    i=0
    while [ "$i" -lt 180 ]; do
      if ${pkgs.curl}/bin/curl -fsS "http://${serverHost}:${toString serverPort}/api/v1/cache/${cacheName}?" >/dev/null 2>&1; then
        break
      fi
      i=$((i + 1))
      sleep 1
    done

    if ! ${pkgs.curl}/bin/curl -fsS "http://${serverHost}:${toString serverPort}/api/v1/cache/${cacheName}?" >/dev/null 2>&1; then
      echo "server endpoint did not become ready in time"
      exit 1
    fi

    ${pkgs.cachix}/bin/cachix config set hostname "http://${serverHost}:${toString serverPort}"

    ${pkgs.cachix}/bin/cachix use "${cacheName}"

    mkdir -p /etc/profile.d
    cat > /etc/profile.d/cache-test-cachix.sh <<'EOF'
    export CACHIX_AUTH_TOKEN='${cacheAuthToken}'
    export CACHIX_AGENT_TOKEN='${agentToken}'
    export CACHIX_ACTIVATE_TOKEN='${activateToken}'
    EOF
  '';

  cachixWrapper = pkgs.writeShellScriptBin "cache-test-cachix" ''
    set -euo pipefail
    export PATH="${pkgs.nix}/bin:${pkgs.coreutils}/bin:${pkgs.gawk}/bin:${pkgs.cachix}/bin:$PATH"
    source /etc/profile.d/cache-test-cachix.sh || true
    exec ${pkgs.cachix}/bin/cachix "$@"
  '';
in {
  lib,
  ...
}: {
  networking.hostName = nodeName;
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];

  services.openssh.enable = true;
  services.openssh.settings = {
    PermitRootLogin = "yes";
    PasswordAuthentication = true;
  };
  users.users.root.initialHashedPassword = lib.mkForce null;
  users.users.root.hashedPasswordFile = lib.mkForce null;
  users.users.root.initialPassword = "root";

  networking.extraHosts = ''
    ${uploadHostIp} ${uploadHostAlias}
  '';

  environment.systemPackages = [
    pkgs.nix
    pkgs.cachix
    pkgs.curl
    pkgs.gawk
    pkgs.jq
    pkgs.python312Packages.pytest
    setupScript
    cachixWrapper
  ];

  environment.etc = if testSource == null then { } else {
    "test".source = testSource;
  };

  systemd.services.cache-test-client-setup = {
    description = "Configure cachix client for blackbox tests";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];

    serviceConfig = {
      Type = "oneshot";
      Restart = "no";
      ExecStart = "${setupScript}/bin/cache-test-client-setup";
    };
  };
}
