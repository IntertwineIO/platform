#!/bin/bash
docker run -v $(pwd):/opt/repos/platform -p 8000:8000 intertwineio/platform ./run.py -p 8000 -d -c dev