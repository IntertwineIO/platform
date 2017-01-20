#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Manages the execution of Intertwine's platform app using docker

Usage:
    run [options] [<command>]

Options:
    -d --debug          Turn on debug
    -C --clean-docker   Clean docker images and containers
    -B --build          (Re)Builds docker image
    -P --push           Pushes docker image
    -R --no-run         Do not run
    -i --image IMAGE    Image to use [default: intertwineio/platform]
'''
import os
from logging import getLogger

import docker

logger = getLogger(__file__)


def cleanup_docker():
    # docker rm -v $(docker ps -a -q -f status=exited)
    # docker rmi $(docker images -f "dangling=true" -q)
    cmd = shlex.split('docker rm -v $(docker ps -a -q -f status=exited)')
    process = subprocess.Popen(cmd)
    process.wait()
    # logger.debug('Started: Cleaning up docker images and containers')
    # client = docker.from_env(assert_hostname=False)
    # Search for the exited containers and remove those
    # /bin/bash: docker rm $(docker ps -a -q)
    # docker rm -v $(docker ps -a -q -f status=exited)
    # removable_containers = {
    #     container['Id'][:12]: container
    #     for container in client.containers(all=True, filters={"status": "exited"})
    # }
    # for container_id, container in removable_containers.items():
    #     client.remove_container(container_id)

    # Search for the images
    # docker rmi $(docker images -f "dangling=true" -q)
    cmd = shlex.split('docker rmi $(docker images -f "dangling=true" -q)')
    process = subprocess.Popen(cmd)
    process.wait()
    # removable_images = {
    #     image['Id'].split(':')[-1][:12]: image
    #     for image in client.images()

    #     if any('<none>' in tag for tag in image['RepoTags'] if image['RepoTags'])
    # }
    # for image_id, image in removable_images.items():
    #     # Force doesn't always remove, but is needed or we error out
    #     client.remove_image(image_id, force=True)
    # logger.debug('Finished: Cleaning up docker images and containers')


def build_docker_image(tags=[]):
    '''Builds a docker image given a path and tags that new image'''


def push_docker_image():
    '''Pushes docker image to docker hub'''


def main(image, build=False, push=False, clean_docker=False, no_run=False, debug=False, command=None):
    local_repo_path = os.path.abspath(os.path.dirname(__file__))
    # client = docker.AutoVersionClient()
    client = docker.from_env(assert_hostname=False)
    host_config = client.create_host_config(
        binds={
            local_repo_path: '/opt/repos/platform',
        },
        read_only=True,
    )

    if clean_docker:
        cleanup_docker()

    if build:
        build_docker_image()

    if push:
        push_docker_image()

    if not no_run:
        command = command or 'vex venv ./run.py -p 8000' + ' -d' if debug else ''
        cmd = 'docker run -v .:/opt/repos/platform -it {image} {command}'
        cmd = cmd.format(image=image, command=command)
        process = subprocess.Popen(cmd)
        process.wait()
        # container = client.create_container(
        #     image=options.get('image'),
        #     command=command,
        #     host_config=host_config,

        # )
        # client.start(container, publish_all_ports=True)
        # print(client.logs(container))


if __name__ == '__main__':
    from docopt import docopt

    options = {
        k.lstrip('-<').rstrip('>').replace('-', '_'): v
        for k, v in docopt(__doc__).items()
    }
    print(options)
    main(**options)

