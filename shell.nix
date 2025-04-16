let
  pkgs = import <nixpkgs> {};
  python = pkgs.python312;
  
  opendht = pkgs.callPackage ./opendht.nix {
    enableProxyServerAndClient = true;
    enablePushNotifications = false;
    Security = if pkgs.stdenv.isDarwin then pkgs.darwin.Security else null;
  };
  
  libPath = "${opendht}/lib";
  pythonSitePackages = "${opendht}/${python.sitePackages}";
in pkgs.mkShell {
  packages = with pkgs; [
    (python.withPackages (ps: with ps; [
      pyjwt websockets ed25519 boto3 pyyaml mypy setuptools cython
    ]))
    cmake pkg-config cppunit
    opendht
  ];
  
  # Set PYTHONPATH to include both the OpenDHT Python bindings and your environment packages
  PYTHONPATH = "${pythonSitePackages}:${python}/${python.sitePackages}";
  
  # Set library paths for both Linux and macOS
  LD_LIBRARY_PATH = "${libPath}:${pkgs.stdenv.cc.cc.lib}/lib";
  DYLD_LIBRARY_PATH = if pkgs.stdenv.isDarwin then "${libPath}" else "";
}
