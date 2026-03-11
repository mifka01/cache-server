{
  description = "cache-server test flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    root.url = "path:..";
  };

  outputs = { self, nixpkgs, root }:
    let
      supportedSystems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);
      mkPkgs = system: import nixpkgs {
        inherit system;
        overlays = [
          (final: prev: {
            msgpack = prev.msgpack-cxx;
          })
        ];
      };
    in
    {
      packages = forAllSystems (system: {
        blackbox-pytest-vm = self.checks.${system}.blackbox-pytest-vm;
        lab-vm = self.checks.${system}.lab-vm;
      });

      apps = forAllSystems (system:
        let
          pkgs = mkPkgs system;
          mkApp = script: {
            type = "app";
            program = script;
          };
          testVmTest = pkgs.writeShellApplication {
            name = "test-vm-test";
            runtimeInputs = [ pkgs.git pkgs.nix pkgs.python3 ];
            text = builtins.readFile ./scripts/test-vm-test.sh;
          };
          lab = pkgs.writeShellApplication {
            name = "lab";
            runtimeInputs = [ pkgs.git pkgs.nix pkgs.bash pkgs.virt-viewer pkgs.tigervnc pkgs.vde2 pkgs.openssh pkgs.sshpass pkgs.gnugrep pkgs.gnused ];
            text = builtins.readFile ./scripts/lab.sh;
          };
          labShell = pkgs.writeShellApplication {
            name = "lab-shell";
            runtimeInputs = [ pkgs.bash pkgs.openssh pkgs.sshpass pkgs.gnugrep pkgs.gnused pkgs.coreutils ];
            text = builtins.readFile ./scripts/lab-shell.sh;
          };
          labStop = pkgs.writeShellApplication {
            name = "lab-stop";
            runtimeInputs = [ pkgs.bash pkgs.coreutils pkgs.procps ];
            text = builtins.readFile ./scripts/lab-stop.sh;
          };
          labStatus = pkgs.writeShellApplication {
            name = "lab-status";
            runtimeInputs = [ pkgs.bash pkgs.coreutils pkgs.gnugrep pkgs.procps ];
            text = builtins.readFile ./scripts/lab-status.sh;
          };
          labLogs = pkgs.writeShellApplication {
            name = "lab-logs";
            runtimeInputs = [ pkgs.bash pkgs.coreutils ];
            text = builtins.readFile ./scripts/lab-logs.sh;
          };
          labClean = pkgs.writeShellApplication {
            name = "lab-clean";
            runtimeInputs = [ pkgs.bash pkgs.coreutils pkgs.gnugrep pkgs.procps ];
            text = builtins.readFile ./scripts/lab-clean.sh;
          };
        in
        {
          default = mkApp "${testVmTest}/bin/test-vm-test";
          pytest = mkApp "${testVmTest}/bin/test-vm-test";
          lab = mkApp "${lab}/bin/lab";
          lab-shell = mkApp "${labShell}/bin/lab-shell";
          lab-stop = mkApp "${labStop}/bin/lab-stop";
          lab-status = mkApp "${labStatus}/bin/lab-status";
          lab-logs = mkApp "${labLogs}/bin/lab-logs";
          lab-clean = mkApp "${labClean}/bin/lab-clean";
        });

      checks = forAllSystems (system:
        let
          pkgs = mkPkgs system;
          cacheServerPkg = pkgs.callPackage "${root}/cache-server.nix" { };
        in
        {
          blackbox-pytest-vm = import "${root}/nix/blackbox/tests/pytest-vm.nix" {
            inherit pkgs cacheServerPkg;
          };
          lab-vm = import "${root}/nix/blackbox/tests/lab-vm.nix" {
            inherit pkgs cacheServerPkg;
          };
        });
    };
}
