#!/usr/bin/env bash

mkdir /var/lib/netTel/
mkdir /var/log/netTel/
mkdir /var/spool/netTel/
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

# this should be done by the setup.py
cd "$(dirname "$0")"

cp -f netTelD/globalNN_for_netTel.h5 /var/lib/netTel/
cp -f netTelD/global_NN_for_netTel_scaler.pkl /var/lib/netTel/
cp -f netTelD/globalNN_for_netTel.h5 netTelD/globalnn_for_nettel.h5
cp -f netTelD/global_NN_for_netTel_scaler.pkl netTelD/global_nn_for_nettel_scaler.pkl


