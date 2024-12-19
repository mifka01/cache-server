{ lib
, python312Packages
}:

python312Packages.buildPythonApplication rec {
  pname = "cache-server";
  version = "1.0";
  pyproject = true;

  src = ./.;

  nativeBuildInputs = [
    python312Packages.setuptools
  ];

  propagatedBuildInputs = [
    python312Packages.pyjwt
    python312Packages.websockets
    python312Packages.ed25519
    python312Packages.boto3
  ];
}
