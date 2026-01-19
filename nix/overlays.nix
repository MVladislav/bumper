# Overlay to provide correct package versions for bumper
final: prev: {
  python313 = prev.python313.override {
    self = final.python313;
    packageOverrides = pyfinal: pyprev: {
      # amqtt 0.11.3 - nixpkgs has old 2022 version missing ClientConfig
      amqtt = pyprev.amqtt.overridePythonAttrs (old: rec {
        version = "0.11.3";
        src = prev.fetchFromGitHub {
          owner = "Yakifo";
          repo = "amqtt";
          rev = "v${version}";
          hash = "sha256-J2BWaUJacsCDa3N9fNohn0l+5Vl4+g8Y8aWetjCfZ/A="; # pragma: allowlist secret
        };

        pyproject = true;

        build-system = with pyfinal; [
          hatchling
          hatch-vcs
        ];

        # Remove old patches that don't apply to new version
        patches = [];

        # Set version since hatch-vcs won't work without git
        env.SETUPTOOLS_SCM_PRETEND_VERSION = version;

        # Patch pyproject.toml to remove uv-dynamic-versioning from build requirements
        postPatch = ''
          substituteInPlace pyproject.toml \
            --replace-fail 'requires = ["hatchling", "hatch-vcs", "uv-dynamic-versioning"]' \
                          'requires = ["hatchling", "hatch-vcs"]'
        '';

        dependencies = with pyfinal; [
          pyyaml
          transitions
          websockets
          passlib
          typer
          dacite
          psutil
        ];

        # Disable strict version check - nixpkgs versions differ
        dontCheckRuntimeDeps = true;

        # Skip tests - they require additional setup
        doCheck = false;
      });
    };
  };
}
