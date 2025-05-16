cd voyager/env/mineflayer || exit
npm install
cd mineflayer-collectblock || exit
npx tsc
cd ..
npm install
cd ../../..