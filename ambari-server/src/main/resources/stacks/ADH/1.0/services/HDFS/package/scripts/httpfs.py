#!/usr/bin/env python
from resource_management import *

class HttpFS(Script):
    def install(self, env):
        # Install packages listed in metainfo.xml
        self.install_packages(env)
        #if any other install steps were needed they can be added here

    #To stop the service, use the linux service stop command and pipe output to log file
    def stop(self, env):
        Execute('service hadoop-httpfs stop')

    #To start the service, use the linux service start command and pipe output to log file
    def start(self, env):
        Execute('service hadoop-httpfs start')

    #To get status of the, use the linux service status command
    def status(self, env):
        Execute('service hadoop-httpfs status')

if __name__ == "__main__":
    HttpFS().execute()
