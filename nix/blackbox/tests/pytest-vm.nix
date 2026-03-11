{ pkgs, cacheServerPkg }:

let
  testSource = pkgs.runCommand "test-suite" { } ''
    mkdir -p "$out"
    cp -r ${../../../test}/* "$out"/
  '';

  cluster = import ../lib/mk-cluster.nix { inherit pkgs cacheServerPkg; } {
    serverSpecs = [
      {
        name = "servera";
        dhtPort = 4222;
        serverPort = 5001;
        deployPort = 6001;
        cachePort = 7001;
        bootstrapHost = "servera";
        bootstrapDhtPort = 4222;
      }
    ];
    clientArgs = {
      inherit testSource;
    };
  };
in
pkgs.testers.runNixOSTest {
  name = "cache-server-pytest-vm";
  inherit (cluster) nodes;

  testScript = ''
    start_all()

    servera.wait_for_unit("cache-server.service")
    client.wait_for_unit("multi-user.target")

    servera.wait_for_open_port(5001)
    servera.wait_for_open_port(7001)

    client.succeed("systemctl start cache-test-client-setup.service")
    client.succeed("test \"$(systemctl show -P Result cache-test-client-setup.service)\" = success")

    token = servera.succeed("sqlite3 /var/lib/cache-server/data/servera.db \"select token from binary_cache where name='main';\"").strip()

    pytest_cmd = "QA_STRICT_API=1 QA_STRICT_NIX_CACHE=1 QA_API_BASE_URL=http://servera:5001 QA_NIX_CACHE_URL=http://servera:7001 QA_CACHE_NAME=main CACHIX_AUTH_TOKEN='{}' pytest -ra -vv /etc/test/tests".format(token)
    client.succeed("bash -o pipefail -c \"{} | tee /tmp/pytest-output.log\"".format(pytest_cmd))
    log.info("pytest output:\n" + client.succeed("cat /tmp/pytest-output.log"))
  '';
}
