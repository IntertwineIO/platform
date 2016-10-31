FROM intertwineio/base
# # ======================================================================
# #  Setup platform
# # ======================================================================
COPY . /opt/repos/platform
WORKDIR /opt/repos/platform
ENV WORKON_HOME /root/.virtualenvs

# Install package
RUN set -ex \
    && cd /opt/repos/platform \
    && vex -m --python python venv pip install --process-dependency-links -e .[all] \
    && vex -m --python python3 venv3 pip install --process-dependency-links -e .[all] \
    # && vex -m --python pypy venvpy pip install --process-dependency-links -e .[all] \
    && apt-get clean autoclean \
    && apt-get autoremove -y \
    && rm -Rf .eggs \
    && rm -rf /var/lib/{apt,dpkg,cache,log}/

CMD ["vex", "venv", "./run.py", "-p", "8000", "-d"]
