# shell.nix
{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python312;
  opendht = pkgs.callPackage ./opendht.nix {
    python = python;
  };

  pythonEnv = python.withPackages (ps: with ps; [
    opendht
    pyjwt
    websockets
    ed25519
    boto3
    pyyaml
    mypy
  ]);
in
pkgs.mkShell {
  buildInputs = [ pythonEnv ];
}

