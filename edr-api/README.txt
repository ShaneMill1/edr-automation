The following will locally download the grib files for the associated model run, aggregate the collections of
parameters based on common dimensions, and create the zarr datastores for the EDR to access.

The ingest currently available are for 1.00, 0.50, and 0.25 degree GFS and 32km NAM
To perform the ingest, you will need to /bin/bash into the running docker container:
docker exec -it <containerID> /bin/bash

From the / Directory:
Commands for Canadian GEM, using 00z run as an example. (Can use 00z, 12z)
/usr/local/bin/python /automated_scripts/create_collections.py gem_25km 00z /media/sf_Transfer/WoW_Data/

Commands for GFS, using 00z run as an example. (Can use 00z, 06z, 12z, 18z)
- 1.00 Degree GFS
/usr/local/bin/python /automated_scripts/create_collections.py gfs_100 00z /media/sf_Transfer/WoW_Data/

- 0.50 Degree GFS
/usr/local/bin/python /automated_scripts/create_collections.py gfs_050 00z /media/sf_Transfer/WoW_Data/

- 0.25 Degree GFS
/usr/local/bin/python /automated_scripts/create_collections.py gfs_025 00z /media/sf_Transfer/WoW_Data/

Command for the NAM, using 00z run as an example. (Can use 00z, 06z, 12z, 18z)
- 32km Nam
/usr/local/bin/python /automated_scripts/create_collections.py nam_32km 00z /media/sf_Transfer/WoW_Data/
