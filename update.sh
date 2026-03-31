clear
git pull --recurse-submodules
git submodule update --remote

cd potd_images
git checkout main
git pull
cd ..

cd qotd_images
git checkout main
git pull
cd ..

python physbot.py