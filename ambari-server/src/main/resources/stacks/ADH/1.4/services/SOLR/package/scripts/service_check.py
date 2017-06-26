#!/usr/bin/env python

import os

from resource_management.core.logger import Logger
from resource_management.core.resources.system import Execute
from resource_management.libraries.functions.format import format
from resource_management.libraries.script import Script
from pprint import pprint

class ServiceCheck(Script):
    def service_check(self, env):
        import params
        env.set_params(params)

        if not os.path.isfile(params.solr_pidfile):
            Logger.error(format("PID file {solr_pidfile} does not exist"))
            exit(1)

        if not params.solr_collection_sample_create:
            Logger.info("Create sample collection unchecked, skipping ...")
            return
	pprint (params)
        if params.solr_cloudmode:
	
            Execute(format(
                         '{solr_bindir}/solr create_collection -c {solr_collection_name} >> {solr_log} 2>&1'
                    ),
                    environment={'JAVA_HOME': params.java64_home},
                    user=params.solr_user
            )
        else:
            Execute(format(
                            '{solr_bindir}/solr create_core -c {solr_collection_name} >> {solr_log} 2>&1'
                    ),
                    environment={'JAVA_HOME': params.java64_home},
                    user=params.solr_user
            )

if __name__ == "__main__":
    ServiceCheck().execute()
