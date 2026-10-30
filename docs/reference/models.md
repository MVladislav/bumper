# Model Compatibility

This page tracks Ecovacs models reported to work with Bumper, known limitations,
and reports that still need clarification.

Model names, `classid` values, and `model` values use
`bumper/web/static_api/productIotMap.json`. Match a robot by its `classid` when
possible; marketing names can cover several variants.
Reports come from project discussions and issues. A missing model has not been
reported here; that does not mean it is unsupported.

## Reported working

These models have been reported to work with Bumper or its previous fork. The
reports do not guarantee current behavior, every feature, or official app support.

> **Note:** The current XMPP implementation appears to be broken, so models that
> worked with earlier versions may no longer work.

### MQTT

| Model Name               | `classid`          | `model`                              | Transport | Firmware          | Issue/Discuss                                                                                                              | Notes                                                            |
| ------------------------ | ------------------ | ------------------------------------ | --------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `DEEBOT 900 Series`      | `ls1ok3`           | `DN5G`                               | MQTT      | -                 | [#121](https://github.com/MVladislav/bumper/discussions/121)                                                               | Reported as working by the previous fork.                        |
| `DEEBOT 600 Series`      | `dl8fht`           | `D600`                               | MQTT      | -                 | -                                                                                                                          | Reported as working by the previous fork.                        |
| `DEEBOT OZMO 950 Series` | `yna5xi`           | `DX9G`                               | MQTT      | -                 | -                                                                                                                          | Reported as working by the previous fork.                        |
| `DEEBOT T10 PLUS`        | `p95mgv`, `rss8xk` | `CURIE_AES_INT_OK`, `CURIE_AES_INT`  | MQTT      | `1.7.2`           | -                                                                                                                          | Confirmed by the maintainer.                                     |
| `DEEBOT T9 AIVI`         | `659yh8`           | `T9_AIVI_INT`                        | MQTT      | -                 | [#277](https://github.com/MVladislav/bumper/discussions/277)                                                               | Reported as compatible.                                          |
| `DEEBOT N8+`             | `7bryc5`, `b2jqs4` | `N8_PLUS_WHITE`, `N8_PLUS_BLACK`     | MQTT      | -                 | [#277](https://github.com/MVladislav/bumper/discussions/277), [#283](https://github.com/MVladislav/bumper/discussions/283) | Reported as compatible.                                          |
| `DEEBOT N8 PRO CARE`     | `s1f8g7`           | `N8_PRO_CARE`                        | MQTT      | -                 | [#288](https://github.com/MVladislav/bumper/discussions/288)                                                               | Reported as compatible.                                          |
| `DEEBOT T20e OMNI`       | `9ku8nu`, `py3qif` | `T20E_OMINI_INT`, `T20E_OMNI_SE_INT` | MQTT      | -                 | [#114](https://github.com/MVladislav/bumper/discussions/114)                                                               | Reported as compatible.                                          |
| `DEEBOT OZMO 920 Series` | `vi829v`           | `DX5G`                               | MQTT      | `1.8.2`           | [#205](https://github.com/MVladislav/bumper/discussions/205)                                                               | Reported as compatible; require RSA rather than EC certificates. |
| `DEEBOT N20`             | `edoodo`, `kr0277` | `Y2_LITE_BLACK_INT`, `Y2_LITE_INT`   | MQTT      | -                 | [#156](https://github.com/MVladislav/bumper/discussions/156)                                                               | Reported as compatible; require RSA rather than EC certificates. |
| `DEEBOT N20 Plus`        | `buom7k`           | `Y2_AES_LITE_INT`                    | MQTT      | -                 | [#290](https://github.com/MVladislav/bumper/discussions/290)                                                               | Reported as compatible; require RSA rather than EC certificates. |
| `DEEBOT X1 OMNI`         | `1vxt52`, `1b23du` | `EINSTEIN_INT`, `EINSTEIN_WHITE_INT` | MQTT      | `1.15.7`, `2.3.9` | [#51](https://github.com/MVladislav/bumper/discussions/51)                                                                 | Reported as possibly compatible.                                 |
| `DEEBOT U2 PRO`          | `7j1tu6`           | `U2_EH2`                             | MQTT      | `1.4.9`           | [#51](https://github.com/MVladislav/bumper/discussions/51)                                                                 | Reported as compatible; may require RSA certificates.            |

### XMPP

| Model Name                   | `classid` | `model` | Transport | Firmware | Issue/Discuss                                                                                                            | Notes                                         |
| ---------------------------- | --------- | ------- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| `DEEBOT OZMO 601`            | `159`     | `159`   | XMPP      | -        | -                                                                                                                        | Reported as working by the previous fork.     |
| `DEEBOT OZMO/PRO 930 Series` | `115`     | `DR930` | XMPP      | -        | [#277](https://github.com/MVladislav/bumper/discussions/277)                                                             | Reported as working by the previous fork.     |
| `DEEBOT M81 Pro`             | `141`     | `M81`   | XMPP      | -        | -                                                                                                                        | Reported as working by the previous fork.     |
| `DEEBOT N79S/SE`             | `155`     | `DN622` | XMPP      | -        | [#97](https://github.com/MVladislav/bumper/discussions/97), [#283](https://github.com/MVladislav/bumper/discussions/283) | Reported issue: queries return empty replies. |
| `DEEBOT N79`                 | `126`     | `N79`   | XMPP      | -        | [#264](https://github.com/MVladislav/bumper/discussions/264)                                                             | Reported issue: entities remain disabled.     |

## Reported model-specific certificate changes

These reports mention a device-specific certificate or key requirement. Standard
deployment setup is not listed as a model-specific change.

### MQTT

| Model Name           | `classid`          | `model`                             | Transport | Firmware  | Issue/Discuss                                              | Notes                                                                                                                            |
| -------------------- | ------------------ | ----------------------------------- | --------- | --------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `GOAT O500 Panorama` | `300lc5`           | `GOAT_BAIZE_500_EU`                 | MQTT      | `1.11.23` | [#81](https://github.com/MVladislav/bumper/discussions/81) | Confirmed by maintainer. See [GOAT certificate guide](https://mvladislav.github.io/bumper/internals/certificate-unpinning-goat). |
| `DEEBOT T10 PLUS`    | `p95mgv`, `rss8xk` | `CURIE_AES_INT_OK`, `CURIE_AES_INT` | MQTT      | `1.7.5`   | -                                                          | Confirmed by maintainer. See [bot certificate guide](https://mvladislav.github.io/bumper/internals/certificate-unpinning-bot).   |

## Reported connection or certificate blockers

These reports describe robots that currently fail to connect or accept commands.
Some reports identify a certificate or TLS limitation; others need more
investigation.

### MQTT

| Model Name        | `classid` | `model`       | Transport | Firmware | Issue/Discuss                                                | Notes                |
| ----------------- | --------- | ------------- | --------- | -------- | ------------------------------------------------------------ | -------------------- |
| `DEEBOT T20 OMNI` | `p1jij8`  | `DARWIN_OMNI` | MQTT      | `1.22.0` | [#114](https://github.com/MVladislav/bumper/discussions/114) | Reported not to run. |

### Bluetooth

| Model Name                     | `classid`                                        | `model`                                                                                                       | Transport | Firmware           | Issue/Discuss                                                | Notes                                          |
| ------------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- | --------- | ------------------ | ------------------------------------------------------------ | ---------------------------------------------- |
| `DEEBOT X9 PRO OMNI`           | `ilt3k8`                                         | `KEPLER_SPRO_BLACK_INT`                                                                                       | Bluetooth | `1.17.0`, `1.42.2` | [#97](https://github.com/MVladislav/bumper/discussions/97)   | Reported not to run; `Cmd interface: disabled` |
| `DEEBOT T80 OMNI`              | `02qwum`, `9eamof`, `aasdks`, `k8qkc7`           | `KEPLER_SE_WHITE_INT`, `KEPLER_SE_BLACK_INT`, `T80`, `KEPLER_SE_WHITE_UP_INT`                                 | Bluetooth | `1.15.0`, `1.36.0` | [#90](https://github.com/MVladislav/bumper/discussions/90)   | Reported not to run; `Cmd interface: disabled` |
| `DEEBOT T30S COMBO`            | `4bdkrs`, `9gqyaq`, `ee23uv`, `kr9c86`, `ue8kcc` | `T30_COMBO_INT_BLACK`, `T30_COMBO_INT`, `T30S_COMBO_COMPLETE`, `T30_COMBO_INT_PRO`, `T30_COMBO_INT_PRO_BLACK` | Bluetooth | `1.95.0`           | [#83](https://github.com/MVladislav/bumper/discussions/83)   | Reported not to run.                           |
| `DEEBOT T90 PRO OMNI`          | `twunby`                                         | `SHAKESPEARE_AM_BLK`                                                                                          | Bluetooth | `1.97.0`           | [#267](https://github.com/MVladislav/bumper/discussions/267) | Reported not to run.                           |
| `DEEBOT X11 (variant unknown)` | -                                                | -                                                                                                             | Bluetooth | -                  | [#186](https://github.com/MVladislav/bumper/discussions/186) | Reported not to run.                           |
| `DEEBOT X8 PRO OMNI`           | `gcu5tt`, `n0vyif`, `uke6j4`, `y72606`           | `KEPLER_WHITE_AI_INT`, `KEPLER_BLACK_AI_INT`, `KEPLER_BLACK_AI_UP_INT`, `KEPLER_BLACK_AI_US_COSTCO`           | Bluetooth | -                  | [#99](https://github.com/MVladislav/bumper/discussions/99)   | Reported not to run.                           |
| `T50 MAX PRO OMNI`             | `c8rj4y`, `qnkybo`                               | `COPERNIC_BLACK_INT`, `COPERNIC_WHITE_INT`                                                                    | Bluetooth | -                  | [#135](https://github.com/MVladislav/bumper/discussions/135) | Reported not to run.                           |

## Needs verification

These entries have conflicting reports, unclear naming, or no confirmed model
variant. The `classid` is the best way to resolve most of them.

### MQTT

| Model Name       | `classid`          | `model`                      | Transport | Firmware | Issue/Discuss                                                | Notes                                        |
| ---------------- | ------------------ | ---------------------------- | --------- | -------- | ------------------------------------------------------------ | -------------------------------------------- |
| `DEEBOT N10`     | `m1wkuw`           | `NOBEL_INT`                  | MQTT      | -        | [#156](https://github.com/MVladislav/bumper/discussions/156) | Check whether RSA certificates are required. |
| `DEEBOT X5 OMNI` | `4jd37g`, `e6yxdm` | `BOHR_INT_WH`, `BOHR_INT_BK` | MQTT      | -        | [#156](https://github.com/MVladislav/bumper/discussions/156) | Check whether RSA certificates are required. |

### Bluetooth

| Model Name       | `classid`          | `model`                         | Transport | Firmware | Issue/Discuss                                              | Notes |
| ---------------- | ------------------ | ------------------------------- | --------- | -------- | ---------------------------------------------------------- | ----- |
| `DEEBOT X2 OMNI` | `e6ofmn`, `lf3bn4` | `X2_OMNI_INT_WH`, `X2_OMNI_INT` | Bluetooth | -        | [#56](https://github.com/MVladislav/bumper/discussions/56) | -     |

### Other or not specified

| Model Name       | `classid` | `model` | Transport | Firmware | Issue/Discuss                                              | Notes |
| ---------------- | --------- | ------- | --------- | -------- | ---------------------------------------------------------- | ----- |
| `GOAT O1000 RTK` | -         | -       | -         | -        | [#81](https://github.com/MVladislav/bumper/discussions/81) | -     |

## Reporting a model

When opening a [discussion](https://github.com/MVladislav/bumper/discussions),
include the `classid`, `model`, firmware version, transport, and whether the
official app or only a client can control the robot. Logs with
`DEBUG_BUMPER_LEVEL=DEBUG` are useful when available.

## Troubleshooting notes

The usual reasons, in the order they are worth checking:

1. **Certificate pinning.**
   The robot ignores the CA and trusts only the
   certificate it shipped with. Check the per-device guides:
   [bot](../internals/certificate-unpinning-bot.md),
   [GOAT](../internals/certificate-unpinning-goat.md),
   [app](../internals/certificate-unpinning-app.md).
2. **Key type.**
   Some robots only offer RSA in their client hello while Bumper
   generates an EC key. Set `CERT_KEY_TYPE=rsa` and `CERT_RSA_KEY_SIZE=2048`.
3. **Transport.**
   Older models speak XMPP, newer ones MQTT, the newest ones NGIoT.
   A model on the wrong transport connects and then answers nothing.
4. **DNS.**
   A robot that still reaches the Ecovacs cloud is not talking to Bumper.
   See [DNS Setup](../getting_started/dns.md).
