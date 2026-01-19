{
  pkgs,
  lib,
  config,
  inputs,
  ...
}: let
  uv = pkgs.uv;
in {
  packages = with pkgs; [
    git
    ruff
    mypy
    openssl
  ];

  env = {
    UV_PYTHON_DOWNLOADS = "never";
    UV_PYTHON_PREFERENCE = "only-system";
  };

  languages.python = {
    enable = true;
    package = pkgs.python313;
    uv = {
      enable = true;
      package = uv;
      sync.enable = false;
    };
    venv = {
      enable = true;
      requirements = null;
    };
  };

  scripts = {
    # Dependency management
    sync.exec = ''
      set -e
      echo "Installing dependencies with uv..."
      uv pip install -r pyproject.toml --all-extras

      echo "Setting up project for development..."
      SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
      DIST_INFO="$SITE_PACKAGES/bumper-0.2.2.dist-info"
      mkdir -p "$DIST_INFO"

      cat > "$DIST_INFO/METADATA" << 'METADATA'
Metadata-Version: 2.1
Name: bumper
Version: 0.2.2
Summary: Deebot Server
METADATA

      cat > "$DIST_INFO/direct_url.json" << EOF
{"dir_info": {"editable": true}, "url": "file://$DEVENV_ROOT"}
EOF

      echo "bumper/__init__.py,," > "$DIST_INFO/RECORD"
      echo "$DEVENV_ROOT" > "$SITE_PACKAGES/bumper-dev.pth"

      echo "Done!"
    '';

    # Build
    build.exec = ''
      echo "Building with nix..."
      nix build .#bumper
      echo "Output: ./result/bin/bumper"
    '';

    # Testing
    test.exec = ''
      pytest "$@"
    '';

    # Linting and formatting
    lint.exec = ''
      echo "Running ruff check..."
      ruff check bumper tests
    '';

    fmt.exec = ''
      echo "Formatting with ruff..."
      ruff format bumper tests
      ruff check --fix bumper tests
    '';

    # Type checking
    typecheck.exec = ''
      echo "Running mypy..."
      mypy bumper
    '';

    # Run all checks
    check.exec = ''
      echo "==> Formatting"
      fmt
      echo ""
      echo "==> Linting"
      lint
      echo ""
      echo "==> Type checking"
      typecheck
      echo ""
      echo "==> Tests"
      test
    '';

    # Run the server
    serve.exec = ''
      python -m bumper "$@"
    '';

    # Show available commands
    dev-help.exec = ''
      echo "Available commands:"
      echo "  sync      - Install/update dependencies"
      echo "  build     - Build package (nix build)"
      echo "  test      - Run tests (pytest)"
      echo "  lint      - Run linter (ruff check)"
      echo "  fmt       - Format code (ruff format)"
      echo "  typecheck - Run type checker (mypy)"
      echo "  check     - Run all checks (fmt, lint, typecheck, test)"
      echo "  serve     - Run the bumper server"
      echo "  dev-help  - Show this help"
    '';
  };

  enterShell = ''
    if [ ! -f "$DEVENV_STATE/venv/.deps-installed" ]; then
      sync
      touch "$DEVENV_STATE/venv/.deps-installed"
    fi

    echo ""
    echo "Bumper Development Environment"
    echo "==============================="
    echo ""
    echo "Commands:"
    echo "  build     - Build package (nix)"
    echo "  test      - Run tests"
    echo "  check     - Run all checks (fmt, lint, typecheck, test)"
    echo "  fmt       - Format code"
    echo "  lint      - Run linter"
    echo "  typecheck - Run type checker"
    echo "  serve     - Run bumper server"
    echo "  sync      - Reinstall dependencies"
    echo ""
  '';

  enterTest = ''
    echo "Running tests"
    python -c "import bumper"
  '';
}
