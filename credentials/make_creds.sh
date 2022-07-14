#!/bin/bash



if [ -z "$CN" ];
then CN=localhost;
fi

if [ -z "$OUT" ];
then OUT=../certs;
fi

echo "CN=${CN}"

mySeedNumber=$$`date +%N`; # seed will be the pid + nanoseconds
myRandomString=$( echo $mySeedNumber | md5sum | md5sum );
mypass="${myRandomString:2:20}"

echo "generating cert keys"
	
# Generate server key:
openssl genrsa -passout pass:${mypass} -des3 -out server.key 4096

# Generate server signing request:
openssl req -passin pass:${mypass} -new -key server.key -out server.csr -subj  "/C=BE/ST=WA/L=Europe/O=Ahriman/OU=Ahriman/CN=${CN}"

# Self-sign server certificate:
openssl x509 -req -passin pass:${mypass} -days 365 -in server.csr -signkey server.key -set_serial 01 -out server.crt

# Remove passphrase from server key:
openssl rsa -passin pass:${mypass} -in server.key -out server.key

rm server.csr
	
cp server.crt server.key $OUT
cp server.crt ~/workspace/ahriman/client/resource/certs
rm -r ~/workspace/ahriman/credentials/out
mkdir ~/workspace/ahriman/credentials/out
cp server.crt server.key ~/workspace/ahriman/credentials/out
echo ${mypass} > $OUT/secret

rm server.crt server.key
