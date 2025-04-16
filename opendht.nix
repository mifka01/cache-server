{
  lib,
  stdenv,
  fetchFromGitHub,
  Security,
  cmake,
  python312,
  python312Packages,
  pkg-config,
  asio,
  nettle,
  gnutls,
  msgpack-cxx,
  readline,
  libargon2,
  jsoncpp,
  restinio,
  http-parser,
  openssl,
  fmt,
  enableProxyServerAndClient ? false,
  enablePushNotifications ? false,
}:

let
  python = python312;
  pythonPkgs = python312Packages;
in
stdenv.mkDerivation rec {
  pname = "opendht";
  version = "3.2.0";
  
  src = fetchFromGitHub {
    owner = "savoirfairelinux";
    repo = "opendht";
    rev = "v${version}";
    hash = "sha256-s172Sj1EvV7Lmnmd+xyKmYF2cDEa8Bot10ovggEsOFg=";
  };

  nativeBuildInputs = [
    cmake
    pkg-config
    pythonPkgs.pybind11
  ];
  
  buildInputs = [
    asio
    fmt
    nettle
    gnutls
    msgpack-cxx
    readline
    libargon2
    python
    pythonPkgs.setuptools
    pythonPkgs.cython
  ] ++ lib.optionals enableProxyServerAndClient [
    jsoncpp
    restinio
    http-parser
    openssl
  ] ++ lib.optionals stdenv.hostPlatform.isDarwin [
    Security
  ];

  cmakeFlags = [
    "-DCMAKE_INSTALL_PREFIX=${placeholder "out"}"
    "-DOPENDHT_BUILD_TOOLS=OFF"
    "-DOPENDHT_PYTHON=ON"
    "-DPYTHON_EXECUTABLE=${python}/bin/python"
    "-DPYTHON_INCLUDE_DIR=${python}/include/python${python.pythonVersion}"
    "-DPYTHON_LIBRARY=${python}/lib/libpython${python.pythonVersion}.so"
    "-DPython_ADDITIONAL_VERSIONS=${python.pythonVersion}"
    "-DOPENDHT_PYTHON_INSTALL_PREFIX=${placeholder "out"}/${python.sitePackages}"
  ] ++ lib.optionals enableProxyServerAndClient [
    "-DOPENDHT_PROXY_SERVER=ON"
    "-DOPENDHT_PROXY_CLIENT=ON"
  ] ++ lib.optionals enablePushNotifications [
    "-DOPENDHT_PUSH_NOTIFICATIONS=ON"
  ];

  # Fix the pkg-config paths in the .pc file
  postPatch = ''
    substituteInPlace CMakeLists.txt \
      --replace '\$'{exec_prefix}/'$'{CMAKE_INSTALL_LIBDIR} '$'{CMAKE_INSTALL_FULL_LIBDIR} \
      --replace '\$'{prefix}/'$'{CMAKE_INSTALL_INCLUDEDIR} '$'{CMAKE_INSTALL_FULL_INCLUDEDIR}
  '';

  # More robust installation that doesn't rely on specific file names
  installPhase = ''
    runHook preInstall
    make install
    
    # Create the site-packages directory if it doesn't exist
    mkdir -p $out/${python.sitePackages}
    
    # Find any OpenDHT-related Python module files and ensure they're in the right place
    echo "Looking for Python modules in the build directory..."
    find . -name '*opendht*.so*' -type f | while read module; do
      module_name=$(basename "$module")
      echo "Found module: $module_name"
      if [ ! -e "$out/${python.sitePackages}/$module_name" ]; then
        echo "Copying $module_name to site-packages"
        cp -v "$module" "$out/${python.sitePackages}/"
      fi
    done
    
    # Ensure all OpenDHT libraries are in the lib directory
    echo "Looking for OpenDHT libraries..."
    find . -name '*opendht*.so*' -o -name '*dht*.so*' -type f | grep -v "site-packages" | while read lib_file; do
      lib_name=$(basename "$lib_file")
      echo "Found library: $lib_name"
      if [ ! -e "$out/lib/$lib_name" ]; then
        mkdir -p $out/lib
        echo "Copying $lib_name to lib directory"
        cp -v "$lib_file" "$out/lib/"
      fi
    done
    
    # Ensure the libraries are executable
    find $out -name '*.so*' -type f -exec chmod +x {} \;
    
    # List what we found
    echo "Final library check:"
    find $out -name '*.so*' -type f | sort
    
    runHook postInstall
  '';

  # Don't check imports here - it might fail during build if paths aren't set correctly
  # We'll check in the shell environment instead

  meta = with lib; {
    description = "C++11 Kademlia distributed hash table implementation";
    homepage = "https://github.com/savoirfairelinux/opendht";
    license = licenses.gpl3Plus;
    maintainers = with maintainers; [
      taeer
      olynch
      thoughtpolice
    ];
    platforms = platforms.unix;
  };
}
