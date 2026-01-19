# NixOS module for Bumper
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.bumper;
in
{
  options.services.bumper = {
    enable = lib.mkEnableOption "Bumper Deebot server";

    package = lib.mkPackageOption pkgs "bumper" { };

    listen = lib.mkOption {
      type = lib.types.str;
      default = "0.0.0.0";
      description = "Address to listen on.";
    };

    announce = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Address to announce to bots on check-in. Defaults to auto-detect.";
    };

    debug = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable debug logging.";
    };

    debugVerbose = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable verbose debug logging.";
    };

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/bumper";
      description = "Directory for bumper data.";
    };

    certsDir = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Directory containing TLS certificates (ca.crt, bumper.crt, bumper.key).";
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "bumper";
      description = "User to run bumper as.";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "bumper";
      description = "Group to run bumper as.";
    };

    openFirewall = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Open firewall ports for bumper (443, 5223, 8007, 8883).";
    };
  };

  config = lib.mkIf cfg.enable {
    users.users.${cfg.user} = lib.mkIf (cfg.user == "bumper") {
      isSystemUser = true;
      group = cfg.group;
      home = cfg.dataDir;
    };

    users.groups.${cfg.group} = lib.mkIf (cfg.group == "bumper") { };

    systemd.services.bumper = {
      description = "Bumper Deebot Server";
      after = [ "network.target" ];
      wantedBy = [ "multi-user.target" ];

      serviceConfig = {
        Type = "simple";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        StateDirectory = "bumper";
        ExecStart = lib.concatStringsSep " " (
          [
            "${cfg.package}/bin/bumper"
            "--listen ${cfg.listen}"
          ]
          ++ lib.optional (cfg.announce != null) "--announce ${cfg.announce}"
          ++ lib.optional cfg.debug "--debug_level 1"
          ++ lib.optional cfg.debugVerbose "--debug_verbose 1"
        );
        Restart = "on-failure";
        RestartSec = 5;

        # Hardening
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        ReadWritePaths = [ cfg.dataDir ];
      };

      environment = lib.mkIf (cfg.certsDir != null) {
        BUMPER_CERTS_PATH = cfg.certsDir;
      };
    };

    networking.firewall = lib.mkIf cfg.openFirewall {
      allowedTCPPorts = [
        443   # HTTPS
        5223  # XMPP
        8007  # XMPP
        8883  # MQTT
      ];
    };
  };
}
