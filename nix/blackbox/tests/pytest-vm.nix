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
    servera.wait_for_open_port(7101)

    client.succeed("systemctl start cache-test-client-setup.service")
    client.succeed("test \"$(systemctl show -P Result cache-test-client-setup.service)\" = success")

    def query(sql):
        return servera.succeed("sqlite3 /var/lib/cache-server/data/servera.db \"{}\"".format(sql)).strip()

    token = query("select token from binary_cache where name='main';")
    cache_id = query("select id from binary_cache where name='main';")
    private_token = query("select token from binary_cache where name='private';")
    workspace_token = query("select token from workspace where name='main';")

    env = " ".join([
        "QA_STRICT_API=1",
        "QA_STRICT_NIX_CACHE=1",
        "QA_API_BASE_URL=http://servera:5001",
        "QA_NIX_CACHE_URL=http://servera:7001",
        "QA_CACHE_NAME=main",
        "QA_CACHE_ID='{}'".format(cache_id),
        "CACHIX_AUTH_TOKEN='{}'".format(token),
        "QA_PRIVATE_CACHE_NAME=private",
        "QA_PRIVATE_NIX_CACHE_URL=http://servera:7101",
        "QA_PRIVATE_CACHE_TOKEN='{}'".format(private_token),
        "QA_WORKSPACE_TOKEN='{}'".format(workspace_token),
        "QA_SERVER_KEY=test-key",
    ])
    pytest_cmd = "{} pytest -ra -vv /etc/test/tests".format(env)
    status, _ = client.execute("bash -o pipefail -c \"{} | tee /tmp/pytest-output.log\"".format(pytest_cmd), timeout=None)
    log.info("pytest output:\n" + client.succeed("cat /tmp/pytest-output.log"))
    assert status == 0, "pytest failed with exit code {}".format(status)
  '';
}
