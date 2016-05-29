#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Manages the execution of Intertwine's platform app using docker

Usage:
    run [options] [<command>]

Options:
    -h --help           This message
    -d --debug          Turn on debug
    -C --clean-docker   Clean docker images and containers
    -B --build          (Re)Builds docker image
'''
import os
from logging import getLogger

import docker

logger = getLogger(__file__)


def cleanup_docker():
    logger.debug('Started: Cleaning up docker images and containers')
    client = docker.from_env(assert_hostname=False)
    # Search for the exited containers and remove those
    # /bin/bash: docker rm $(docker ps -a -q)
    removable_containers = {
        container['Id'][:12]: container
        for container in client.containers(all=True, filters={"status": "exited"})
    }
    for container_id, container in removable_containers.items():
        client.remove_container(container_id)

    # Search for the images
    # /bin/bash: docker rmi $(docker images | grep "^<none>" | awk "{print $3}")
    removable_images = {
        image['Id'].split(':')[-1][:12]: image
        for image in client.images()
        if any('<none>' in tag for tag in image['RepoTags'])
    }
    for image_id, image in removable_images.items():
        # Force doesn't always remove, but is needed or we error out
        client.remove_image(image_id, force=True)
    logger.debug('Finished: Cleaning up docker images and containers')


def build_docker_image(tags=[]):
    '''Builds a docker image given a path and tags that new image'''


def push_docker_image():
    '''Pushes docker image to docker hub'''


def main(**options):
    client = docker.from_env(assert_hostname=False)
    local_repo_path = os.path.abspath(os.path.dirname(__file__))

    if options.get('clean-docker'):
        cleanup_docker()

    repo_name = os.path.dirname(__file__)
    build_docker_image(tags=['intertwineio/{repo_name}'.format(repo_name)])


    container = client.create_container(
        image='platform',
        command=command,
        host_config=client.create_host_config(binds={
            local_repo_path: '/opt/repos/platform',
        })

    )
    client.start(container, publish_all_ports=True)



if __name__ == '__main__':
    from docopt import docopt

    options = {
        k.lstrip('-<').rstrip('>').replace('-', '_'): v
        for k, v in docopt(__doc__).items()
    }
    main(**options)

