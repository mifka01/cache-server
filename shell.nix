let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (python-pkgs: [
        python-pkgs.pyjwt
        python-pkgs.websockets
        python-pkgs.ed25519
        python-pkgs.boto3
        python-pkgs.pyyaml
        python-pkgs.mypy
    ]))
  ];
}

