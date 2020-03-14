docker build -t edr-lean .
docker run -d -v /host/directory/data:/media/sf_Transfer/WoW_Data/ -p 5000:5000 edr-lean
