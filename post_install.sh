#!/usr/bin/env bash

mkdir /var/lib/netTel/
mkdir /var/log/netTel/
mkdir /var/spool/netTel/input/
mkdir /var/spool/netTel/output/

# configure the keras backend to use theano
# maybe this should be done done somewhere else?
mkdir ~/.keras/
touch ~/.keras/keras.json
cat > ~/.keras/keras.json <<EOL
{
    "image_dim_ordering": "tf",
    "epsilon": 1e-07,
    "floatx": "float32",
    "backend": "theano"
}
EOL
