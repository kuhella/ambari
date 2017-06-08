'''
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

from resource_management.libraries.functions import format
from resource_management.libraries.script.script import Script
import os
import os.path


# config object that holds the configurations declared in the -config.xml file
config = Script.get_config()

# RPM versioning support
# rpm_version = default("/configurations/cluster-env/rpm_version", None)

# store the ambari stack service dir
service_package_folder = '/var/lib/ambari-agent/cache/stacks/HDP/2.1/services/SMARTSENSE/package'
log_dir = '/var/log/hst'
ambari_service_log = os.path.join(log_dir, 'ambari-service.log')
hst_conf_dir = '/etc/hst/conf'
log4j_conf_file = os.path.join(hst_conf_dir, 'log4j.properties');
hst_win_service_name = 'hst'
hst_pid_dir = '/var/run/hst'
server_conf_file_name = 'hst-server.ini'
agent_conf_file_name = 'hst-agent.ini'
hst_install_home = '/usr/hdp/share/hst'
hst_agent_home = os.path.join(hst_install_home, 'hst-agent')
hst_server_home = os.path.join(hst_install_home, 'hst-server')
capture_levels_json = os.path.join(hst_conf_dir, 'capture_levels.json')
anonymization_rules_json = os.path.join(hst_conf_dir, 'anonymization_rules.json')
smartsense_packages = ["smartsense-hst"]
hst_shell_cmds_dir = os.path.join(service_package_folder, 'files')
hst_view_dir = os.path.join(hst_shell_cmds_dir, 'view')
hst_view_conf_xml = os.path.join(hst_view_dir, 'view.xml')
hst_default_view_template = os.path.join(hst_view_dir, 'view_default.xml')
hst_instance_view_template = os.path.join(hst_view_dir, 'view_instance.xml')
hst_view_jar_file_name = 'smartsense*view*.jar'
hst_view_jar_file_path = os.path.join(hst_view_dir, hst_view_jar_file_name)
hst_view_jar = os.path.join(hst_view_dir, hst_view_jar_file_name)
ambari_view_dir = "/var/lib/ambari-server/resources/views"
ambari_agent_data_dir = "/var/lib/ambari-agent/data/"
install_view_tmp_dir="/tmp/smartsense-view/"



hst_tool_cleanup_directories = [
                                '/etc/hst',
                                '/var/log/hst',
                                '/var/run/hst',
                                log_dir,
                                hst_conf_dir,
                                hst_pid_dir
                                ]

hst_view_instance_cleanup_directories = [
                                         os.path.join(ambari_view_dir, "work", "SMARTSENSE*"),
                                         os.path.join(ambari_view_dir, "work", "HORTONWORKS_SMARTSENSE*")
                                         ]

hst_view_cleanup_directories = [
                                os.path.join(ambari_view_dir, "smartsense*")
                                ]

ambari_service_server_cleanup_directories = [
                                  "/var/lib/ambari-server/resources/stacks/HDP/2.1/services/SMARTSENSE"
                                 ]

ambari_service_agent_cleanup_directories = [
                                  "/var/lib/ambari-agent/cache/stacks/HDP/2.1/services/SMARTSENSE"
                                 ]

server_owned_dirs = [
                    '/etc/hst',
                    '/var/log/hst',
                    '/var/run/hst',
                    log_dir,
                    hst_conf_dir,
                    hst_pid_dir,
                    "/var/lib/smartsense",                  
                    "/var/lib/smartsense/hst-common",                  
                    "/var/lib/smartsense/hst-server"                    
                    ]

agent_owned_dirs = [
                    '/etc/hst',
                    '/var/log/hst',
                    log_dir,
                    hst_conf_dir,
                    "/var/lib/smartsense/hst-agent"                    
                    ]

if ('hst-server-conf' in config['configurations'] and 'server.storage.dir' in config['configurations']['hst-server-conf']) :
    hst_tool_cleanup_directories.append(config['configurations']['hst-server-conf']['server.storage.dir'])
    server_owned_dirs.append(config['configurations']['hst-server-conf']['server.storage.dir'])

if ('hst-server-conf' in config['configurations'] and 'server.tmp.dir' in config['configurations']['hst-server-conf']) :
    hst_tool_cleanup_directories.append(config['configurations']['hst-server-conf']['server.tmp.dir'])
    server_owned_dirs.append(config['configurations']['hst-server-conf']['server.tmp.dir'])

if ('hst-agent-conf' in config['configurations'] and 'server.tmp_dir' in config['configurations']['hst-agent-conf']) :
    hst_tool_cleanup_directories.append(config['configurations']['hst-agent-conf']['agent.tmp_dir'])
    agent_owned_dirs.append(config['configurations']['hst-agent-conf']['agent.tmp_dir'])


# Configurations
hst_common_config = None
if ('hst-common-conf' in config['configurations']) :
    hst_common_config = config['configurations']['hst-common-conf']

hst_server_config = None
if ('hst-server-conf' in config['configurations']) :
    hst_server_config = config['configurations']['hst-server-conf']

hst_agent_config = None
if ('hst-agent-conf' in config['configurations']) :
    hst_agent_config = config['configurations']['hst-agent-conf']

# Env properties
if 'hst-env' in config['configurations']:
    if 'hst_pid_dir' in config['configurations']['hst-env']:
        hst_pid_dir = config['configurations']['hst-env']['hst_pid_dir']
    if 'log_dir' in config['configurations']['hst-env']:
        log_dir = config['configurations']['hst-env']['log_dir']
    if 'hst_conf_dir' in config['configurations']['hst-env']:
        hst_conf_dir = config['configurations']['hst-env']['hst_conf_dir']

# Path to HST PID file.
hst_pid_file = os.path.join(hst_pid_dir, 'hst-server.pid')

hst_server_host = 'localhost'
if 'clusterHostInfo' in config and 'hst_server_hosts' in config['clusterHostInfo']:
    hst_server_host = config['clusterHostInfo']['hst_server_hosts'][0]
