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

    # Server-side checks; every one runs so a failing run reports all of them.
    cli = "XDG_CONFIG_HOME=/var/lib cache-server"
    failures = []

    def check(name, command):
        code, output = servera.execute(command, timeout=180)
        log.info("server check {}: {}\n{}".format(name, "ok" if code == 0 else "FAILED", output))
        if code != 0:
            failures.append(name)

    def port_closed(port):
        return "timeout 60 sh -c 'while ss -Hltn \"sport = :{}\" | grep -q .; do sleep 1; done'".format(port)

    def port_open(port):
        return "timeout 120 sh -c 'until ss -Hltn \"sport = :{}\" | grep -q .; do sleep 1; done'".format(port)

    # `grep -q` would stop reading at the first match and make the CLI fail with
    # BrokenPipeError under the driver's pipefail; `has` reads the whole output.
    def has(command, line):
        return f"{command} | grep -x '{line}' >/dev/null"

    check("cli cache info", has(f"{cli} cache info main", "Name: main"))
    check("cli cache list", has(f"{cli} cache list", "main"))
    check("cli workspace list", has(f"{cli} workspace list", "main"))
    check("cli store-path info", f"h=$({cli} store-path list main | sed -n 1p) && test -n \"$h\" && " + has(f"{cli} store-path info \"$h\" main", "Store hash: $h").replace("'", "\""))
    check("cli workspace create/delete", f"{cli} workspace create cliws main && " + has(f"{cli} workspace info cliws", "Binary cache: main") + f" && {cli} workspace delete cliws && ! {cli} workspace info cliws")
    check("cli agent add/list/delete", f"{cli} agent add cliagent main && " + has(f"{cli} agent list main", "cliagent") + f" && {cli} agent delete cliagent && ! " + has(f"{cli} agent list main", "cliagent"))
    check("cli cache create", f"{cli} cache create clitest --port 7201 --root /var/lib/cache-server/caches --access private --retention 3 && " + has(f"{cli} cache info clitest", "Access: private"))
    check("cli cache update", f"{cli} cache update clitest --port 7202 --retention 5 && " + has(f"{cli} cache info clitest", "Port: 7202") + " && " + has(f"{cli} cache info clitest", "Retention: 5"))

    # KillMode=process: only the server itself gets SIGTERM and must stop its cache processes.
    check("SIGTERM stops cache processes", "systemctl kill --kill-whom=main --signal=SIGTERM cache-server.service && " + port_closed(7001) + " && " + port_closed(7101))
    check("restart after SIGTERM", "systemctl restart cache-server.service && " + port_open(7001))
    check("cache missing from config is kept", has(f"{cli} cache info clitest", "Name: clitest") + " && journalctl -u cache-server.service | grep 'WARNING: Binary cache clitest' >/dev/null")
    check("cli cache delete", f"{cli} cache delete clitest && ! {cli} cache info clitest")

    assert status == 0, "pytest failed with exit code {}".format(status)
    assert not failures, "server checks failed: {}".format(", ".join(failures))
  '';
}
