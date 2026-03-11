{
  description = "cache-server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);
      mkPkgs = system: import nixpkgs {
        inherit system;
        overlays = [
          (final: prev: {
            # Compatibility shim: recent nixpkgs split `msgpack` into
            # `msgpack-c` and `msgpack-cxx`, while opendht.nix expects `msgpack`.
            msgpack = prev.msgpack-cxx;
          })
        ];
      };
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = mkPkgs system;
          cacheServerPkg = pkgs.callPackage ./cache-server.nix { };
        in
        {
          default = cacheServerPkg;
          cache-server = cacheServerPkg;
        });

      devShells = forAllSystems (system:
        let
          pkgs = mkPkgs system;
          python = pkgs.python312;
          opendht = pkgs.callPackage ./opendht.nix { inherit python; };
          pythonEnv = python.withPackages (ps: with ps; [
            opendht
            pyjwt
            websockets
            ed25519
            boto3
            pyyaml
            mypy
            pytest
            types-pyyaml
          ]);
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              pythonEnv
              pkgs.cachix
              pkgs.curl
              pkgs.jq
            ];
          };

          rust = pkgs.mkShell {
            buildInputs = [
              pkgs.rustc
              pkgs.cargo
              pkgs.clippy
              pkgs.rustfmt
              pkgs.rust-analyzer
              pkgs.pkg-config
              pkgs.openssl
            ];
          };
        });
    };
}
