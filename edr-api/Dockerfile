FROM debian:latest

RUN apt-get update && apt-get -y install vim curl bzip2 libzstd-dev libssl-dev libopenblas-base libopenblas-dev \
    && curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -bfp /usr/local \
    && rm -rf /tmp/miniconda.sh \
    && apt-get -qq -y remove curl bzip2 \
    && apt-get -qq -y autoremove \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log \
    && conda clean --all --yes

ENV PATH /opt/conda/bin:$PATH
RUN conda install -c conda-forge libiconv requests flask flask-cors click pyyaml unicodecsv xarray dask netCDF4 bottleneck 
RUN conda install -c conda-forge dicttoxml pynio pyproj metpy xmltodict shapely fiona regionmask zarr gdal
RUN conda install -c conda-forge python-eccodes pandas bs4 python-wget  

ENV FLASK_APP=/WoW/wow_point_server.py
ENV WoW_CONFIG=/WoW/config/config.yml

COPY ./start.sh /start.sh
COPY ./automated_scripts /automated_scripts
COPY WoW /WoW
COPY ./README.txt /README.txt

RUN chmod +x /start.sh

WORKDIR /
EXPOSE 5000

CMD ["./start.sh"]


