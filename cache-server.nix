{ lib, python312, callPackage, stdenv, cmake, pkg-config, cppunit }:

let
  python = python312;

  opendht = callPackage ./opendht.nix {
    inherit python;
  };

  pythonPackages = python.pkgs;

in
pythonPackages.buildPythonApplication rec {
  pname = "cache-server";
  version = "1.0";
  pyproject = true;
  src = ./.;

  nativeBuildInputs = [
    pkg-config
    cppunit
    pythonPackages.setuptools
  ];

  propagatedBuildInputs = with pythonPackages; [
    pyjwt
    websockets
    ed25519
    boto3
    pyyaml
    mypy
    cython
    opendht
  ];
}

