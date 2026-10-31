# Toolchain for scripts/app/create-unpinned-app.sh.
#
# Everything the app patching needs runs in here, so the host only needs docker:
# a JDK (keytool, apksigner), the Android build-tools (zipalign), python3 for the
# two patchers, and curl/unzip for fetching and unpacking the XAPK.
FROM eclipse-temurin:21-jdk-jammy

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      curl unzip zip libc++1 python3 \
 && rm -rf /var/lib/apt/lists/*

# zipalign links against the unversioned SONAME libc++.so; Ubuntu ships only
# libc++.so.1, so provide the alias.
RUN ln -sf "$(ldconfig -p | awk '/libc\+\+\.so\.1 /{print $NF; exit}')" /usr/local/lib/libc++.so \
 && ldconfig

RUN mkdir -p /opt/build-tools \
 && curl -sSL -o /tmp/bt.zip https://dl.google.com/android/repository/build-tools_r34-linux.zip \
 && unzip -qo /tmp/bt.zip -d /tmp/bt \
 && cp /tmp/bt/*/zipalign /tmp/bt/*/lib/apksigner.jar /opt/build-tools/ \
 && cp -r /tmp/bt/*/lib /opt/build-tools/lib \
 && rm -rf /tmp/bt /tmp/bt.zip

ENV PATH=/opt/build-tools:$PATH \
    LD_LIBRARY_PATH=/opt/build-tools/lib:/usr/local/lib

# The patchers are copied in so the container always uses this directory's copy.
# Editing one only invalidates this layer, not the toolchain above.
COPY *.py build-apks.sh /opt/apk-patch/
RUN chmod +x /opt/apk-patch/build-apks.sh

ENTRYPOINT ["/opt/apk-patch/build-apks.sh"]
