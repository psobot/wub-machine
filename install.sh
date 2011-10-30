#!/bin/bash

platform='unknown'
packagemanager='unknown'
unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
   packagemanager='apt-get'
elif [[ "$unamestr" == 'Darwin' ]]; then
   platform='macosx'
   packagemanager='brew'
fi
if [[ $platform == 'unknown' ]]; then
    echo "Unknown platform detected - OS X and Ubuntu currently supported."
    exit 1
fi

if [ "$(id -u)" != "0" ]; then
	echo "This installer requires root permissions - please run sudo ./install.sh instead"'!'
	exit 1
fi

echo "------------------------------------------------------"
echo "------ INSTALLING THE WUB MACHINE'S DEPENDENCIES -----"
echo "----------  Be careful, this might not work ----------"
echo "--------- In fact, this might screw things up --------"
echo "-- I take no responsibility if something goes wrong. -"
echo "------------------------------------------------------"
echo "-- Really, all this script does is run a bunch of   --"
echo "-- $packagemanager installs and pip installs.                  --"
echo "-- A little bit of code is downloaded from Github.  --"
echo "-- You'll get FFMpeg, LAME, SoundStretch, SHNtool...--"
echo "------------------------------------------------------"
echo
read -p "Do you agree and take all responsibility if something goes wrong? (y/n): " RESP
if [ $RESP != "y" ]; then
  echo "Exiting."
  exit 0
fi

hash $packagemanager 2>&- || { echo >&2 "This installer requires $packagemanager."; exit 1; }

# Install Python-dev
if [[ $platform == 'linux' ]]; then
    apt-get install git-core python-setuptools python-dev build-essential python-pip

    # Install server-specific stuff: SQLAlchemy, Tornadio, Tornadio from HEADs
    apt-get install python-mysqldb
    pip install sqlalchemy

    git clone https://github.com/facebook/tornado.git
    cd tornado
    python setup.py install
    cd ..
    rm -rf tornado/

    git clone https://github.com/MrJoes/tornadio.git
    cd tornadio
    python setup.py install
    cd ..
    rm -rf tornadio/

    # Other handy things
    apt-get install libyaml-dev
    pip install pyyaml
    pip install numpy
    pip install mutagen

    apt-get install libjpeg-dev
    pip install PIL

    # The Echo Nest Remix API
    apt-get install ffmpeg
    sudo ln -s `which ffmpeg` /usr/local/bin/en-ffmpeg
    git clone https://github.com/echonest/remix.git
    cd remix
    git clone https://github.com/echonest/pyechonest pyechonest
    python setup.py install
    cd ..
    rm -rf remix/

    # Command-line programs used to speed up remixing
    apt-get install lame soundstretch shntool

else
    hash easy_install 2>&- || hash pip 2>&- || { echo >&2 "This installer requires easy_install or pip."; exit 1; }
    hash pip 2>&- || easy_install pip

    # Install server-specific stuff: SQLAlchemy, Tornadio, Tornadio from HEADs
    pip install python-mysqldb
    pip install sqlalchemy

    git clone https://github.com/facebook/tornado.git
    cd tornado
    python setup.py install
    cd ..
    rm -rf tornado/

    git clone https://github.com/MrJoes/tornadio.git
    cd tornadio
    python setup.py install
    cd ..
    rm -rf tornadio/

    # Other handy things
    brew install libyaml
    pip install pyyaml
    pip install numpy
    pip install mutagen

    brew install jpeg
    pip install PIL

    # The Echo Nest Remix API
    hash ffmpeg 2>&- || brew install ffmpeg
    sudo ln -s `which ffmpeg` /usr/local/bin/en-ffmpeg
    git clone https://github.com/echonest/remix.git
    cd remix
    git clone https://github.com/echonest/pyechonest pyechonest
    python setup.py install
    cd ..
    rm -rf remix/

    # Command-line programs used to speed up remixing
    brew install lame
    
    wget "http://www.surina.net/soundtouch/soundstretch_mac_osx_x64_1.6.0.zip"
    unzip "soundstretch_mac_osx_x64_1.6.0.zip"
    mv ./soundstretch /usr/bin/soundstretch
    rm "soundstretch_mac_osx_x64_1.6.0.zip"
    
    brew install shntool
fi
