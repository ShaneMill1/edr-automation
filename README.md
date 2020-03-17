# edr-automation
This is an implementation of the Environmental Data Retrieval API to test grib ingestion

Navigate to edr-api. In the docker.cmd file, you will need to change the volume path to a path on the local host system where
data will be stored. I recommend it being outside of the file path that contains the Dockerfile so that when you rebuild 
the docker image, it doesn't take long to do so. A directory above the Dockerfile is perfectly fine.

Once you have updated the docker.cmd file, run ./docker.cmd. This will build the image and run the container.
Once complete, the container should be viewable at http://localhost:5000.

To ingest data, go to the README in edr-api
