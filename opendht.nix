{
    lib,
    python,
    fetchFromGitHub,
    stdenv,
    autogen,
    automake,
    autoconf,

    libtool,
    pkg-config,
    cppunit,

    nettle,
    gnutls,
    msgpack,
    libargon2,
    fmt,
    asio,
}:

python.pkgs.buildPythonPackage rec {
    pname = "opendht";
    version = "3.2.0";

    src = fetchFromGitHub {
        owner = "savoirfairelinux";
        repo = "opendht";
        rev = "v${version}";
        hash = "sha256-s172Sj1EvV7Lmnmd+xyKmYF2cDEa8Bot10ovggEsOFg=";
    };

    nativeBuildInputs = [
        autogen
        automake
        autoconf
        libtool
        pkg-config
        cppunit

        python.pkgs.cython
        python.pkgs.pip
    ];

    buildInputs = [
        nettle
        gnutls
        msgpack
        libargon2
        fmt
        asio
        python.pkgs.setuptools
    ];

    buildPhase = ''
        # prefix is used for rpath of .so file
        bash ./autogen.sh && ./configure --disable-tools --prefix="$out"

        # this is needed because of nix store permissions
        make DESTDIR="$TMPDIR" install
    '';

    installPhase = ''
        runHook preInstall

        mkdir -p $out/${python.sitePackages}

        cp -r $TMPDIR/$out/lib/* $out/lib/
        cp -r $TMPDIR/${python}/${python.sitePackages}/* $out/${python.sitePackages}/

        runHook postInstall
      '';

    # dont use setuptools
    format = "other";

    doCheck = false;
}

