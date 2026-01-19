{
  description = "Bumper - Deebot Server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    devenv.url = "github:cachix/devenv";
    devenv-root = {
      url = "file+file:///dev/null";
      flake = false;
    };
    systems.url = "github:nix-systems/default";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    devenv,
    devenv-root,
    systems,
    ...
  }: let
    forEachSystem = nixpkgs.lib.genAttrs (import systems);
    overlays = [
      (import ./nix/overlays.nix)
    ];
  in {
    inherit overlays;

    packages = forEachSystem (system: let
      pkgs = import nixpkgs {
        inherit system overlays;
      };
      python = pkgs.python313;
    in {
      default = self.packages.${system}.bumper;
      bumper = python.pkgs.buildPythonApplication {
        pname = "bumper";
        version = "0.2.2";
        pyproject = true;

        src = ./.;

        # Patch pyproject.toml to use setuptools instead of uv_build
        postPatch = ''
          substituteInPlace pyproject.toml \
            --replace-fail 'requires = ["uv_build>=0.8.0"]' 'requires = ["setuptools>=61.0"]' \
            --replace-fail 'build-backend = "uv_build"' 'build-backend = "setuptools.build_meta"'

          # Remove uv_build config and add setuptools package discovery
          cat >> pyproject.toml << 'EOF'

          [tool.setuptools.packages.find]
          include = ["bumper*"]
          EOF
        '';

        build-system = [
          python.pkgs.setuptools
        ];

        dependencies = with python.pkgs; [
          aiodns
          aiofiles
          aiohttp-jinja2
          aiohttp
          aiomqtt
          amqtt
          cachetools
          coloredlogs
          cryptography
          defusedxml
          jinja2
          passlib
          pyjwt
          tinydb
          validators
          websockets
        ];

        # Disable checks - nixpkgs package versions may differ from requirements
        dontCheckRuntimeDeps = true;
        pythonImportsCheck = [];

        meta = {
          description = "Deebot Server";
          homepage = "https://github.com/bmartin5692/bumper";
          license = pkgs.lib.licenses.gpl3Only;
          mainProgram = "bumper";
        };
      };
    });

    devShells = forEachSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      devenvRootFileContent = builtins.readFile devenv-root.outPath;
      devenvRootFromEnv = builtins.getEnv "DEVENV_ROOT";
      devenvRootFromPwd = builtins.getEnv "PWD";
    in {
      default = devenv.lib.mkShell {
        inherit inputs pkgs;
        modules = [
          ({...}: {
            devenv.root = let
              devenvRoot =
                if devenvRootFileContent != ""
                then devenvRootFileContent
                else if devenvRootFromEnv != ""
                then devenvRootFromEnv
                else if devenvRootFromPwd != ""
                then devenvRootFromPwd
                else builtins.throw "Use direnv or run with --impure";
            in
              devenvRoot;
          })
          ./devenv.nix
        ];
      };
    });
  };
}
