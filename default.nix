{ python311 }:

let python = python311;
in python.pkgs.buildPythonPackage {
  pname = "mitmproxy-remote-interceptions";
  version = "0.1.0";

  src = ./.;
  format = "pyproject";

  propagatedBuildInputs = with python.pkgs; [
    mitmproxy
    websockets
  ];
}
