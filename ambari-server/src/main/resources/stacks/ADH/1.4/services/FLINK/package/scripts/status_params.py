#!/usr/bin/env python
from resource_management import *
import sys, os

config = Script.get_config()

flink_pid_dir=config['configurations']['flink-env']['flink_pid_dir']
flink_pid_file=flink_pid_dir + '/flink-flink-jobmanager.pid'

flink_home_dir=config['configurations']['flink-env']['flink_home_dir']
