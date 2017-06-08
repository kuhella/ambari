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

from resource_management import *
import os
import os.path
import string
import random
import ConfigParser
import subprocess
import getpass
import re
import utils
import time



class HSTScript(Script):

    ##################### Directly exposed functions through Ambari #####################
    def __init__(self, component=None):
        self.component = component

    def install(self, env):

        self.install_packages()
        # packages must be deployed before deploying configs
        self.hst_deploy_component_specific_config()
        if self.component is 'agent':
            #self.run_agent_setup()
            print("No specific install steps for agent")
        elif self.component is 'server':
            self.run_server_setup()
            # Find ambari host and install HST view
        # At this time, we dont know which hosts has ambari server running.
        # So Issue view installation for all hosts, only ambari host will pick it up
        self.install_smartsense_view()


  # Exposed through Ambari service action named "Uninstall_HST"
    def uninstall_hst(self, env):
        self.uninstall_hst_packages()

  # Exposed through Ambari service action named "Wipe_Out_Hst"
    def wipe_out_hst(self, env):
        # First remove rpms
        self.uninstall_hst(env)
        # Then remove any data created by HST
        self.remove_hst_data()

    # Configuration setting based on configs specified in ambari
    def configure(self, env):
        self.hst_deploy_component_specific_config()


    # Start all SmartSense services
    def start(self, env):
        # Before start deploy the latest configs
        self.hst_deploy_component_specific_config()
        if self.component is 'server':
            self.start_hst_server()
        elif self.component is 'agent':
            # Agent does not have any start command but register it through setup
            self.run_agent_setup()

    # Stop all SmartSense services
    def stop(self, env):
        if self.component is 'server':
            self.stop_hst_server()
        elif self.component is 'agent':
            try:
                self.unregister(env)
            except:
                print ("Could not gracefully stop as server seems to be down. Stopping anyways.")
                pass

    def status(self, env):
        import params
        if self.component is 'server':
            # use built-in method to check status using pidfile
            print ("Pid file: " + str(params.hst_pid_file))
            check_process_status(params.hst_pid_file)
        elif self.component is 'agent':
            # Check if agent is registered. If registered, then status is alive anything else is dead
            status_cmd = "{sudo} /usr/sbin/hst agent-status"
            exit_code, output, error = self.execute_command(status_cmd)
            if (exit_code == 0 or exit_code == None) and output.strip().lower() == 'registered':
                pass
            else:
                raise ComponentIsNotRunning()



    # Exposed through Ambari service action named "Register"
    def register(self, env):
        if self.component is 'agent':
            self.run_agent_setup()
        # Server does not have register command

    # Exposed through Ambari service action named "Unregister"
    def unregister(self, env):
        if self.component is 'agent':
            cmd = "{sudo} /usr/sbin/hst unregister-agent"
            exit_code, output, error = self.execute_command(cmd)

    # Exposed through Ambari service action named "Capture"
    def capture(self, env):
        # Only agent has capture command
        if self.component is 'agent':
            config = Script.get_config()
            params = config['commandParams']
            service = 'ALL'
            if params and 'service' in params:
                service = params['service']

            case_number = 0
            if params and 'caseNumber' in params:
                case_number = params['caseNumber']

            capture_level = 'L2'
            if params and 'level' in params:
                capture_level = params['level']

            services_to_collect_list = self.find_services_to_collect(service)

            if services_to_collect_list:
                services_to_collect = ",".join(services_to_collect_list)

                print("services_to_collect: " + services_to_collect)


                cmd = '{sudo} /usr/sbin/hst capture "%s" "%s" "%s" &' % (services_to_collect, case_number, capture_level)
                try:
                    exit_code, output, error = self.execute_command(cmd, background=True)
                except Exception, e:
                    message = "Error executing HST capture command.\n" + str(e)
                    print message
                    raise Fail(message)
            else:
                print("No matching services found on this host. Skipping capture.")

    # Exposed through Ambari service action named "Uninstall_Smartsense_View"
    def uninstall_smartsense_view(self, env):
        import params
        # Try uninstalling only if this is ambari host, else ignore.
        if self.am_i_ambari_server() == True:
            print("This is found to be ambari server host. Uninstalling the SmartSense view.")
            for dir in params.hst_view_instance_cleanup_directories:
                cmd = "{sudo} rm -rf " + dir
                exit_code, output, error = self.execute_command(cmd)


            cmd = 'mkdir -p ' + params.install_view_tmp_dir + ' ; cp ' + params.hst_view_jar_file_path + ' ' + params.install_view_tmp_dir + ' ; cp ' + params.hst_instance_view_template + ' ' + params.install_view_tmp_dir + 'view.xml'
            print("Removing view instance definition by creating a view copy")
            exit_code, output, error = self.execute_command(cmd)

            cmd = 'cd ' + params.install_view_tmp_dir + ' ; ' + params.config['hostLevelParams']['java_home'] + '/bin/jar uf ' + params.hst_view_jar_file_name + ' view.xml'
            print("Adding default view configs to view jar")
            exit_code, output, error = self.execute_command(cmd)

            cmd = "{sudo} cp " + params.install_view_tmp_dir + params.hst_view_jar_file_name + " " + params.ambari_view_dir + os.sep
            print("Uninstalling HST view")
            exit_code, output, error = self.execute_command(cmd)

            cmd = 'cd /tmp;  rm -rf "' + params.install_view_tmp_dir + '"'
            print("Cleaning temporary view directory : " + cmd)
            exit_code, output, error = self.execute_command(cmd)


        else:
             print ("This is not ambari server host so no view to uninstall.")


    # Exposed through Ambari service action named "Wipe_Out_Smartsense_View"
    def wipe_out_smartsense_view(self, env):
        import params
        # Try wipe out only if this is ambari host, else ignore.
        if self.am_i_ambari_server() == True:
            print("This is found to be ambari server host. Removing the SmartSense view.")
            # first remove the view instance
            self.uninstall_smartsense_view(env)

            for dir in params.hst_view_instance_cleanup_directories:
                cmd = "{sudo} rm -rf " + dir
                exit_code, output, error = self.execute_command(cmd)

            for dir in params.hst_view_cleanup_directories:
                cmd = "{sudo} rm -rf " + dir
                exit_code, output, error = self.execute_command(cmd)

        else:
             print ("This is not ambari server host so no view to remove.")

    def uninstall(self, env):
        self.wipe_out_all(env)

    def wipe_out_all(self, env):
        self.wipe_out_smartsense_view(env)
        self.wipe_out_hst(env)
        # self.wipe_out_smartsense_ambari_service(); Since the service is going to be part of Ambari itself, it is not to be cleaned during SmartSense uninstall
    ##################### Internal  functions  #####################

    def run_server_setup(self):
        cmd = "/usr/sbin/hst setup -q --nostart --nocheck"
        print("Setting up HST server")
        exit_code, output, error = self.execute_command(cmd)


    def run_agent_setup(self):
        cmd = "{sudo} /usr/sbin/hst setup-agent -q &"
        try:
            exit_code, output, error = self.execute_command(cmd, background=True)
        except Exception, e:
            message = "Error starting HST agent \n" + str(e)
            print message
            raise Fail(message)

    def start_hst_server(self):
        cmd = '/usr/sbin/hst start '
        exit_code, output, error = self.execute_command(cmd)

    def stop_hst_server(self):
        import params
        cmd = '/usr/sbin/hst stop '
        exit_code, output, error = self.execute_command(cmd)
        # delete the pid file
        exit_code, output, error = self.execute_command('rm -f "' + params.hst_pid_file + '"')

    def install_packages(self):
        import params
        import time
        distname, version = utils.get_os()
        major_version = version.split(".")[0]

        if distname.startswith('ubuntu') or distname.startswith('debian'):
            cmd = "{sudo} dpkg-query -l  | grep  'ii\s*smartsense-*' || {sudo} apt-get -o Dpkg::Options::=--force-confdef --allow-unauthenticated --assume-yes install smartsense-hst || {sudo} dpkg -i " + os.path.join(params.service_package_folder, "files" , "deb", "*.deb")
        elif distname.startswith('sles') or distname.startswith('suse'):
            cmd = "{sudo} rpm -qa | grep smartsense- || {sudo} zypper install --auto-agree-with-licenses --no-confirm smartsense-hst || {sudo} rpm -i " + os.path.join(params.service_package_folder, "files" , "rpm", "*.rpm")
        else:
            cmd = "{sudo} rpm -qa | grep smartsense- || {sudo} yum -y install smartsense-hst || {sudo} rpm -i " + os.path.join(params.service_package_folder, "files" , "rpm", "*.rpm")
        print("installing using command: " + cmd)

        attempts = 0
        while attempts < 10:
            attempts += 1
            try:
                exit_code, output, error = self.execute_command(cmd)
                if ( exit_code == 0):
                    break
            except Exception, e:
                print "Failed to install during attempt " % (attempts)
                print e
            if ( attempts < 3 ):
                print "Waiting 5 seconds for next retry"
                time.sleep(5)

    def uninstall_hst_packages(self):
        import params
        distname, version = utils.get_os()
        removal_command = ""
        for package in params.smartsense_packages:
            if distname.startswith('ubuntu') or distname.startswith('debian'):
                removal_command = '{sudo} ! dpkg-query -l  | grep  "ii\s*' + package + '" || {sudo} apt-get -y remove ' + package + ' || {sudo} dpkg -r ' + package
            elif distname.startswith('sles') or distname.startswith('suse'):
                removal_command = "{sudo} ! rpm -qa | grep " + package + " || {sudo} zypper remove --no-confirm " + package + " || {sudo} rpm -e " + package
            else:
                removal_command = "{sudo} ! rpm -qa | grep " + package + " || {sudo} yum -y erase " + package + " || {sudo} rpm -e " + package
            print("Uninstalling using command: " + removal_command)
            exit_code, output, error = self.execute_command(removal_command)



    def remove_hst_data(self):
        import params
        for dir in params.hst_tool_cleanup_directories:
            cmd = "{sudo} rm -rf " + dir
            exit_code, output, error = self.execute_command(cmd)

    def hst_deploy_component_specific_config(self):
        import params

        # Before changing configs make sure it has right permissions to read
        self.set_permissions()
        # Always deploy agent configs as all hosts are expected to have agent configs.
        conf_file_name = params.agent_conf_file_name
        conf_params = params.hst_agent_config
        self.hst_deploy_config(conf_file_name, conf_params)

        # Additionally if it is a server also deploy server configs
        if self.component is 'server':
            conf_file_name = params.server_conf_file_name
            conf_params = params.hst_server_config
            self.hst_deploy_config(conf_file_name, conf_params)

        # After changing configs make sure it has right permissions
        self.set_permissions()

    def hst_deploy_config(self, conf_file_name, conf_params):
        import params
        import os

        config_file_path = os.path.join(params.hst_conf_dir, conf_file_name)

        # Derive java home from ambari and set it
        java_home = params.config['hostLevelParams']['java_home']
        # print("java_home="+str(java_home))

        # Derive cluster name from ambari and set it
        cluster_name = params.config['clusterName']
        # print("cluster_name="+str(cluster_name))

        # Derive if cluster is secured
        security_enabled = str(params.config['configurations']['cluster-env']['security_enabled']).lower()
        # print("security_enabled="+str(security_enabled))

        config = ConfigParser.RawConfigParser()
        config.read(config_file_path)
        config.set('server', 'hostname', params.hst_server_host)
        config.set('java', 'home', java_home)
        config.set('cluster', 'name', cluster_name)
        config.set('cluster', 'secured', security_enabled)

        if params.hst_common_config != None:
            for k, v in params.hst_common_config.iteritems():
                key = k.split(".", 1)
                if (len(key) != 2):
                    raise Fail("Configuration property should be named in the form <section name>.<property name>")

                # print("Setting common config " + str(k) + '=' + str(v))
                if ( not config.has_section(key[0]) ):
                    config.add_section (key[0])
                config.set(key[0], key[1], v)

        if conf_params != None:
            for k, v in conf_params.iteritems():
                # print("Setting server config " + str(k) + '=' + str(v))
                key = k.split(".", 1)
                if (len(key) != 2):
                    raise Fail("Configuration property should be named in the form <section name>.<property name>")
                if ( not config.has_section(key[0]) ):
                    config.add_section (key[0])
                config.set(key[0], key[1], v)

        if config_file_path.endswith("server.ini") :
            if ( (not config.has_option('server', 'run.as.user')) or config.get('server', 'run.as.user') == None or config.get('server', 'run.as.user').strip == ""  ):
                if ( "root" != getpass.getuser()):
                    config.set('server', 'run.as.user', getpass.getuser())

        print("Writing configs to : " + str(config_file_path))

        #First write to temp file and then rename to avoid partial written files.
        with open(config_file_path + ".tmp", 'w') as config_file:
            config.write(config_file)
        os.rename(config_file_path + ".tmp", config_file_path)


        # # Write capture levels
        # No need to write to tmp as whole content is in Ambari and partial written files will be auto fixed on retry
        capture_levels = None
        if 'capture-levels' in params.config['configurations'] and 'capture-levels-content' in params.config['configurations']['capture-levels']:
            capture_levels = params.config['configurations']['capture-levels']['capture-levels-content']
        if (capture_levels != None):
            File(format(params.capture_levels_json),
            mode=0644,
            content=capture_levels
            )


        # # Write anonymization rules
        # No need to write to tmp as whole content is in Ambari and partial written files will be auto fixed on retry
        anonymization_rules = None
        if 'anonymization-rules' in params.config['configurations'] and 'anonymization-rules-content' in params.config['configurations']['anonymization-rules']:
            anonymization_rules = params.config['configurations']['anonymization-rules']['anonymization-rules-content']
        if (anonymization_rules != None):
            File(format(params.anonymization_rules_json),
            mode=0644,
            content=anonymization_rules
            )

        # # Write log4j
        # No need to write to tmp as whole content is in Ambari and partial written files will be auto fixed on retry
        log4j_props = None
        if ('hst-log4j' in params.config['configurations']) and ('hst-log4j-content' in params.config['configurations']['hst-log4j']):
            log4j_props = params.config['configurations']['hst-log4j']['hst-log4j-content']
        if (log4j_props != None):
            File(format(params.log4j_conf_file),
            mode=0644,
            content=log4j_props
            )

    def find_host_services(self):
        import params

        # Note: Keep all service names and roles lower case
        host_services = ['ambari']  # These services are expected to be available on all hosts by default
        current_host = params.config['hostname']

        # Note: Keep all service names and roles lower case
        service_component_mapping = {'accumulo':['accumulo_master', 'accumulo_monitor', 'accumulo_gc', 'accumulo_tracer', 'accumulo_tserver', 'accumulo_client'],
            'ams':['metrics_collector', 'metrics_monitor'],
            'atlas':['atlas_server'],
            'falcon':['falcon_client', 'falcon_server'],
            'flume':['flume', 'flume_handler'],
            'ganglia':['ganglia_server', 'ganglia_monitor'],
            'hbase':['hbase_master', 'hbase_regionserver', 'hbase_rs', 'hbase_client'],
            'hdfs':['namenode', 'datanode', 'secondary_namenode', 'hdfs_client', 'journalnode', 'zkfc', 'slave'],
            'hive':['hive_metastore', 'hive_server', 'webhcat_server', 'mysql_server', 'hive_client', 'hcat'],
            'kafka':['kafka_broker'],
            'kerberos':['kerberos_client'],
            'knox':['knox_gateway'],
            'mahout':['mahout'],
            'oozie':['oozie_server', 'oozie_client'],
            'pig':['pig'],
            'ranger':['ranger_admin', 'ranger_usersync', 'ranger_kms_server'],
            'slider':['slider'],
            'spark':['spark_jobhistoryserver', 'spark_client'],
            'sqoop':['sqoop'],
            'storm':['nimbus', 'storm_rest_api', 'supervisor', 'storm_ui_server', 'drpc_server'],
            'tez':['tez_client'],
            'yarn':['resourcemanager', 'nodemanager', 'yarn_client', 'historyserver', 'rm', 'nm', 'slave'],
            'zk':['zookeeper', 'zookeeper_server', 'zookeeper_client'],
            'mr': ['mapreduce2_client', 'historyserver'],
            'nagios': ['nagios']
            }

        # Unfortunately, Ambari does not pass on client role information in the custom command json.
        # So we need alternative approch to find if there this host is also playing client rols
        #
        service_client_file_name_mapping = {'accumulo':['ACCUMULO_CLIENT'],
            'atlas':['ATLAS_CLIENT'],
            'falcon':['FALCON_CLIENT'],
            'hbase':['HBASE_CLIENT'],
            'hdfs':['HDFS_CLIENT'],
            'hive':[ 'HIVE_CLIENT'],
            'kafka':['KAFKA_CLIENT'],
            'kerberos':['KERBEROS_CLIENT'],
            'mahout':['MAHOUT_CLIENT'],
            'oozie':['OOZIE_CLIENT'],
            'pig':['PIG', 'PIG_CLIENT'],
            'slider':['SLIDER', 'SLIDER_CLIENT'],
            'spark':[ 'SPARK_CLIENT'],
            'sqoop':['SQOOP', 'SQOOP_CLIENT'],
            'storm':['STORM_CLIENT'],
            'tez':['TEZ_CLIENT'],
            'yarn':[ 'YARN_CLIENT'],
            'zk':['ZOOKEEPER_CLIENT'],
            'mr': ['MAPREDUCE2_CLIENT', 'MAPREDUCE_CLIENT']
            }
        for service, components in service_component_mapping.iteritems():
            found = False
            for component in components:
                for host_role, host_list in params.config['clusterHostInfo'].iteritems():
                    if ((host_role.startswith(service) or host_role.startswith(component)) and current_host in host_list) :
                     host_services.append(service)
                     found = True
                     break
                if found: break

        print("Mapped services to host: " + str(host_services))

        # Check if there are any client roles
        for service, client_file_names in service_client_file_name_mapping.iteritems():
            # If this service is not already mapped only then check for client
            if (service not in host_services):
                for client_file_name in client_file_names:
                    if (os.path.isfile(params.ambari_agent_data_dir + "/" + client_file_name + "_config.json")):
                         host_services.append(service)
                         break ;

        print("Mapped services along with clients host: " + str(host_services))
        return host_services

    def find_services_to_collect(self, triggered_services):
        import params

        print("triggered_services: " + triggered_services)

        available_services = self.find_host_services()
        supported_services = self.find_supported_services()

        if triggered_services.lower() == 'all':
            return set(available_services).intersection(supported_services)
        else:
            requested_services = triggered_services.lower().split(",")
        return set(requested_services).intersection (available_services).intersection(supported_services)

    def find_supported_services(self):
        import params
        cmd = "{sudo} /usr/sbin/hst list-services"
        exit_code, output, error = self.execute_command(cmd)
        if exit_code == 0:
            return set(re.findall(r"[\w']+", output.lower()))
        else:
            return ['ambari', 'falcon', 'ganglia', 'hbase', 'hcatalog', 'hdfs', 'hive', 'kafka', 'knox', 'mr', 'nagios', 'oozie', 'pig', 'ranger', 'spark', 'sqoop', 'storm', 'tez', 'yarn', 'zk']

    def install_smartsense_view(self):
        import params

        # Try installing only if this is ambari host, else ignore.
        current_host = params.config['hostname']
        if self.am_i_ambari_server() == True:
            print("This is found to be ambari server host. Installing the SmartSense view.")
            cmd = ' rm -rf "' + params.install_view_tmp_dir + '"'
            print("Cleaning temporary view directory pre install: " + cmd)
            exit_code, output, error = self.execute_command(cmd)


            if 'server.ssl_enabled' in params.hst_server_config and params.hst_server_config['server.ssl_enabled'] == True :
                protocol = "https"
            else:
                protocol = "http"
            port = params.hst_server_config['server.port']

            print("Creating view instance definition")

            cmd = 'mkdir -p ' + params.install_view_tmp_dir + ' ; cp ' + params.hst_view_jar_file_path + ' ' + params.install_view_tmp_dir + ' ; cp ' + params.hst_instance_view_template + ' ' + params.install_view_tmp_dir + 'view.xml'
            exit_code, output, error = self.execute_command(cmd)

            cmd = "sed -i -- 's/\${server_url}/" + protocol + "\:\/\/" + params.hst_server_host + "\:" + str(port) + "/g' " + params.install_view_tmp_dir + "view.xml"
            exit_code, output, error = self.execute_command(cmd)

            cmd = 'cd ' + params.install_view_tmp_dir + ' ; ' + params.config['hostLevelParams']['java_home'] + '/bin/jar uf ' + params.hst_view_jar_file_name + ' view.xml'
            exit_code, output, error = self.execute_command(cmd)

            cmd = "{sudo} cp " + params.install_view_tmp_dir + params.hst_view_jar_file_name + " " + params.ambari_view_dir + os.sep
            print("Deploying HST view")
            exit_code, output, error = self.execute_command(cmd)
            cmd = "{sudo} chmod 644 " + params.ambari_view_dir + os.sep + params.hst_view_jar_file_name
            exit_code, output, error = self.execute_command(cmd)



            cmd = 'cd /tmp;  rm -rf "' + params.install_view_tmp_dir + '"'
            print("Cleaning temporary view directory post install: " + cmd)
            exit_code, output, error = self.execute_command(cmd)

        else:
            print ("This is not ambari server host so nothing to install.")


    def am_i_ambari_server(self):
        import params
        # Try installing only if this is ambari host, else ignore.
        current_host = params.config['hostname']
        print ("This host is identified as " + current_host + " and ambari server is identified as " + str(params.config['clusterHostInfo']['ambari_server_host']))
        if current_host in params.config['clusterHostInfo']['ambari_server_host']:
            return True
        else:
            return False

    def wipe_out_smartsense_ambari_service(self):
        import params
        cleanup_commands = "";
        for dir in params.ambari_service_agent_cleanup_directories:
            cleanup_commands = cleanup_commands + os.linesep + "{sudo} rm -rf " + dir + ";"
        for dir in params.ambari_service_server_cleanup_directories:
            cleanup_commands = cleanup_commands + os.linesep + "{sudo} rm -rf " + dir + ";"

        # Self clean the script
        cleanup_commands = cleanup_commands + os.linesep + '{sudo} rm -- "$0"'

        cleanup_script = '/tmp/smartsense_service_cleanup.sh'
        print ("Generating cleanup command")
        File(format(cleanup_script),
            mode=0700,
            content=cleanup_commands
            )

        print("Cleaning up HST")
        exit_code, output, error = self.execute_command(cleanup_script)

    def set_permissions(self):
        import params
        run_as_user=""
        if self.component is 'agent':
            dir_list = params.agent_owned_dirs
        elif self.component is 'server':
            dir_list = params.server_owned_dirs
            server_config = ConfigParser.RawConfigParser()
            server_config.read(os.path.join(params.hst_conf_dir, params.server_conf_file_name))
            if ( server_config.has_section('server') and server_config.has_option('server', 'run.as.user') ):
               run_as_user = server_config.get('server', 'run.as.user')

        if ( run_as_user == None or run_as_user.strip() == ""):
            run_as_user = getpass.getuser()
        id_cmd = 'id -gn ' + run_as_user
        p = subprocess.Popen([id_cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        output, error = p.communicate()
        if (p.returncode == 0 or p.returncode == None) :
            group = output.strip()
        else:
            group = output.user()

        for dir in dir_list :
            cmd = "{sudo} mkdir -p " + dir
            exit_code, output, error = self.execute_command(cmd)

            cmd = "{sudo} chown -R " + run_as_user + ":" + group + " " + dir
            exit_code, output, error = self.execute_command(cmd)


    def get_sudo_command(self):
        if os.geteuid() == 0:
            return ""
        else:
            return "sudo"

    def execute_command(self, command, background=False):
        print ("Command to be executed:" +command)
        normalized_command = command.replace("{sudo}", self.get_sudo_command())
        print ("Normalized command:" + normalized_command)

        if ( background == True):
            p = subprocess.Popen(normalized_command, shell=True)
            # Wait for process to spawn
            time.sleep(3)
            return (0,None,None )

        p = subprocess.Popen(normalized_command, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
        stdout, stderr = p.communicate()
        code = p.wait()
        print("Exit code: " + str(code))
        print("stdout: " + str(stdout))
        print("stderr: " + str(stderr))
        return (code, stdout, stderr)
if __name__ == "__main__":
    HSTScript().execute()
