#!/usr/bin/env bash

BASE_PATH="${PWD}/certs"
mkdir -p "${BASE_PATH}"
# Possible to much, but better have than not :D
SUBJECT_ALT_NAME='subjectAltName=IP:127.0.0.1,DNS:localhost,DNS:*.a1zYhiMF5J3.iot-as-mqtt.cn-shanghai.aliyuncs.com,DNS:*.eu-central-1.aliyuncs.com,DNS:*.iot-as-mqtt.cn-shanghai.aliyuncs.com,DNS:*.itls.eu-central-1.aliyuncs.com,DNS:*.openaccount.aliyun.com,DNS:*.aliyun.com,DNS:*.aliyuncs.com,DNS:*.api-app.dc-eu.ww.ecouser.net,DNS:*.api-app.ww.ecouser.net,DNS:*.api-base.dc-eu.ww.ecouser.net,DNS:*.api-ngiot.dc-eu.ww.ecouser.net,DNS:*.app.cn.ecouser.net,DNS:*.app.ww.ecouser.net,DNS:*.area.cn.ecouser.net,DNS:*.area.robotcn.ecouser.net,DNS:*.area.robotww.ecouser.net,DNS:*.area.ww.ecouser.net,DNS:*.as.dc.ww.ecouser.net,DNS:*.autodiscover.ecovacs.com,DNS:*.base.cn.ecouser.net,DNS:*.base.ww.ecouser.net,DNS:*.bizcn.ecouser.net,DNS:*.bizww.ecouser.net,DNS:*.ca.robotcn.ecouser.net,DNS:*.ca.robotww.ecouser.net,DNS:*.cfjump.ecovacs.com,DNS:*.checkout-au.ecovacs.com,DNS:*.checkout-test.ecovacs.com,DNS:*.checkout-uk.ecovacs.com,DNS:*.cloud-ui.dc-as.cloud.ww.ecouser.net,DNS:*.cloud-ui.dc-cn.cloud.cn.ecouser.net,DNS:*.cloud-ui.dc-eu.cloud.ww.ecouser.net,DNS:*.cloud-ui.dc-na.cloud.ww.ecouser.net,DNS:*.cloud.cn.ecouser.net,DNS:*.cloud.ww.ecouser.net,DNS:*.cn-shanghai.aliyuncs.com,DNS:*.cn.dc.cn.ecouser.net,DNS:*.cn.ecouser.net,DNS:*.codepush-base.dc-na.ww.ecouser.net,DNS:*.comingsoon.ecovacs.com,DNS:*.czjquw.ecovacs.com,DNS:*.dc-as.app.ww.ecouser.net,DNS:*.dc-as.base.ww.ecouser.net,DNS:*.dc-as.bizww.ecouser.net,DNS:*.dc-as.cloud.ww.ecouser.net,DNS:*.dc-as.ngiot.ww.ecouser.net,DNS:*.dc-as.rapp.ww.ecouser.net,DNS:*.dc-as.rop.ww.ecouser.net,DNS:*.dc-as.ww.ecouser.net,DNS:*.dc-aus.ww.ecouser.net,DNS:*.dc-cn.app.cn.ecouser.net,DNS:*.dc-cn.base.cn.ecouser.net,DNS:*.dc-cn.bizcn.ecouser.net,DNS:*.dc-cn.cloud.cn.ecouser.net,DNS:*.dc-cn.cn.ecouser.net,DNS:*.dc-cn.ngiot.cn.ecouser.net,DNS:*.dc-cn.rapp.cn.ecouser.net,DNS:*.dc-cn.rop.cn.ecouser.net,DNS:*.dc-eu.app.ww.ecouser.net,DNS:*.dc-eu.base.ww.ecouser.net,DNS:*.dc-eu.bizww.ecouser.net,DNS:*.dc-eu.cloud.ww.ecouser.net,DNS:*.dc-eu.ngiot.ww.ecouser.net,DNS:*.dc-eu.rapp.ww.ecouser.net,DNS:*.dc-eu.rop.ww.ecouser.net,DNS:*.dc-eu.ww.ecouser.net,DNS:*.dc-hq.cn.ecouser.net,DNS:*.dc-hq.devhq.ecouser.net,DNS:*.dc-na.app.ww.ecouser.net,DNS:*.dc-na.base.ww.ecouser.net,DNS:*.dc-na.bizww.ecouser.net,DNS:*.dc-na.cloud.ww.ecouser.net,DNS:*.dc-na.ngiot.ww.ecouser.net,DNS:*.dc-na.rapp.ww.ecouser.net,DNS:*.dc-na.rop.ww.ecouser.net,DNS:*.dc-na.ww.ecouser.net,DNS:*.dc.cn.ecouser.net,DNS:*.dc.ecouser.net,DNS:*.dc.robotcn.ecouser.net,DNS:*.dc.robotww.ecouser.net,DNS:*.dc.ww.ecouser.net,DNS:*.dev.ecouser.net,DNS:*.devhq.ecouser.net,DNS:*.dl.ecouser.net,DNS:*.ecouser.net,DNS:*.ecovacs.com,DNS:*.eis-nlp.dc-eu.ww.ecouser.net,DNS:*.eml.ecovacs.com,DNS:*.eu.dc.ww.ecouser.net,DNS:*.exchange.ecovacs.com,DNS:*.gl-de-api.ecovacs.com,DNS:*.gl-de-openapi.ecovacs.com,DNS:*.gl-us-pub.ecovacs.com,DNS:*.jmq-ngiot-eu.dc.robotww.ecouser.net,DNS:*.lb.ecouser.net,DNS:*.lbo.ecouser.net,DNS:*.mail.ecovacs.com,DNS:*.mpush-api.aliyun.com,DNS:*.msg-eu.ecouser.net,DNS:*.na.dc.ww.ecouser.net,DNS:*.ngiot.cn.ecouser.net,DNS:*.ngiot.ww.ecouser.net,DNS:*.parts-apac.ecovacs.com,DNS:*.portal-ww-qa.ecouser.net,DNS:*.portal-ww-qa1.ecouser.net,DNS:*.portal-ww.ecouser.net,DNS:*.qdbdrg.ecovacs.com,DNS:*.rapp.cn.ecouser.net,DNS:*.rapp.ww.ecouser.net,DNS:*.recommender.ecovacs.com,DNS:*.robotcn.ecouser.net,DNS:*.robotww.ecouser.net,DNS:*.rop.cn.ecouser.net,DNS:*.rop.ww.ecouser.net,DNS:*.sa-eu-datasink.ecovacs.com,DNS:*.sdk.openaccount.aliyun.com,DNS:*.site-static.ecovacs.com,DNS:*.store-de.ecovacs.com,DNS:*.store-fr.ecovacs.com,DNS:*.store-it.ecovacs.com,DNS:*.store-jp.ecovacs.com,DNS:*.store-uk.ecovacs.com,DNS:*.storehk.ecovacs.com,DNS:*.storesg.ecovacs.com,DNS:*.users-base.dc-eu.ww.ecouser.net,DNS:*.usshop.ecovacs.com,DNS:*.vpn.ecovacs.com,DNS:*.ww.ecouser.net,DNS:*.www.ecouser.net,DNS:*.www.eml.ecovacs.com,DNS:aliyun.com,DNS:aliyuncs.com,DNS:ecouser.net,DNS:ecovacs.com'

if [ ! -f "${BASE_PATH}/ca.crt" ] || [ ! -f "${BASE_PATH}/ca.key" ] || [ ! -f "${BASE_PATH}/bumper.crt" ] || [ ! -f "${BASE_PATH}/bumper.key" ]; then
   echo "Creating CA certificate..."
   openssl ecparam -name prime256v1 -genkey -out "${BASE_PATH}/ca.key"
   openssl req -new -x509 -sha256 -days 6669 -key "${BASE_PATH}/ca.key" -out "${BASE_PATH}/ca.crt" \
   -subj "/O=ecovacs/CN=ECOVACS CA" \
   -extensions v3_ca \
   -config <(
     echo "[req]"
     echo "distinguished_name=req"
     echo "x509_extensions=v3_ca"
     echo "[req]"
     echo "[v3_ca]"
     echo "basicConstraints = critical, CA:true"
     echo "keyUsage = critical, keyCertSign, cRLSign"
     echo "subjectKeyIdentifier = hash"
   )
   chmod 600 "${BASE_PATH}/ca.key"

  echo "Creating Server certificate..."
  openssl ecparam -name prime256v1 -genkey -out "${BASE_PATH}/bumper.key"
  openssl req -new -sha256 -key "${BASE_PATH}/bumper.key" -out "${BASE_PATH}/bumper.csr" \
    -subj "/O=ecovacs/CN=*.ecouser.net" \
    -config <(
      : 'cat /etc/ssl/openssl.cnf ; \'
      echo '[req]'
      echo 'distinguished_name=req'
      echo 'req_extensions=v3_req'
      echo 'x509_extensions=v3_req'
      echo "[v3_req]"
      echo "keyUsage = critical, digitalSignature"
      echo "extendedKeyUsage = serverAuth"
      echo "${SUBJECT_ALT_NAME}"
    )

  openssl x509 -req -in "${BASE_PATH}/bumper.csr" -CA "${BASE_PATH}/ca.crt" -CAkey "${BASE_PATH}/ca.key" -CAcreateserial \
    -sha256 -days 666 -out "${BASE_PATH}/bumper.crt" \
    -extensions v3_req \
    -extfile <(
      : 'cat /etc/ssl/openssl.cnf ; \'
      echo '[req]'
      echo 'distinguished_name=req'
      echo 'req_extensions=v3_req'
      echo 'x509_extensions=v3_req'
      echo "[v3_req]"
      echo "keyUsage = critical, digitalSignature"
      echo "extendedKeyUsage = serverAuth"
      echo "${SUBJECT_ALT_NAME}"
    ) 2>/dev/null

  echo "Create ca.pem..."
  cat "${BASE_PATH}/bumper.key" >"${BASE_PATH}/ca.pem"
  cat "${BASE_PATH}/bumper.crt" >>"${BASE_PATH}/ca.pem"
  cat "${BASE_PATH}/ca.crt" >>"${BASE_PATH}/ca.pem"

  echo "Cleaning up temporary files..."
  rm "${BASE_PATH}/bumper.csr"
  rm "${BASE_PATH}/ca.srl"

  echo "Certificates created successfully in ${BASE_PATH}"
else
  echo "All needed certificate files already exist, nothing to do!"
fi
