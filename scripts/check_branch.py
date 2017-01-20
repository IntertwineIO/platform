#!/usr/bin/env python
# -*- coding: utf-8 -*-
from git import Repo

repo = Repo()
branch_name = repo.active_branch.name
if branch_name != 'master':
    raise RuntimeError('Branch "{}" is not "master".  Release halted.'.format(branch_name))
