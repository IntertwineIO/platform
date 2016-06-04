FROM intertwineio/base
# # ======================================================================
# #  Setup platform
# # ======================================================================
COPY . /opt/repos/platform
WORKDIR /opt/repos/platform

# Install package
RUN python -m pip install --process-dependency-links -e . \
    && python -m pip install --process-dependency-links .[all] \
    && apt-get clean autoclean \
    && apt-get autoremove -y \
    && rm -Rf .eggs \
    && rm -rf /var/lib/{apt,dpkg,cache,log}/

CMD ["./run.py", "-p", "8000", "-d"]
