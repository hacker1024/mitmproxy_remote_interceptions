{ writeShellApplication, runCommandNoCC, buildEnv, python311 }:

let
  python = python311;

  mitmproxy-remote-interceptions = python.pkgs.buildPythonPackage {
    pname = "mitmproxy-remote-interceptions";
    version = "0.1.0";
    format = "pyproject";

    src = ./.;

    propagatedBuildInputs = with python.pkgs; [ mitmproxy websockets ];
  };

  launchers = let
    tools = [ "dump" "proxy" "web" ];
    launcher = writeShellApplication {
      name = "mitmri";
      runtimeInputs = [ (python.withPackages (ps: [ mitmproxy-remote-interceptions ])) ];
      text = ''
        mitmricommand="$(basename "$0")"
        ''${mitmricommand/mitmri/mitm} "$@" -s "$(python -c 'import importlib.util; print(importlib.util.find_spec("mitmproxy_remote_interceptions").origin)')"
      '';
    };
  in runCommandNoCC "mitmproxy-remote-interceptions-launchers" { } ''
    mkdir -p $out/bin
    ${builtins.concatStringsSep "\n"
    (map (tool: "ln -s ${launcher}/bin/${launcher.name} $out/bin/mitmri${tool}") tools)}
  '';
in buildEnv {
  name = "mitmproxy-remote-interceptions-env";
  paths = [ (python.withPackages (ps: [ mitmproxy-remote-interceptions ])) launchers ];
}
