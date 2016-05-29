FROM python:2

# Setup platform
COPY . /opt/repos/platform
WORKDIR /opt/repos/platform

# Setup environment
RUN python -m pip install uwsgi uwsgitop \
    && python -m pip install --process-dependency-links -e /opt/repos/platform \
    && apt-get clean autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/{apt,dpkg,cache,log}/

#ENTRYPOINT ["./run.py"]
CMD ["./run.py", "-p", "8000", "-d"]
