from resource_management.core.logger import Logger
from resource_management.core.resources.system import Execute, File
from resource_management.libraries.functions.check_process_status import check_process_status
from resource_management.libraries.functions.format import format
from resource_management.libraries.script.script import Script

from setup_solr import setup_solr
from setup_solr_cloud import setup_solr_cloud
from setup_solr_hdfs_support import setup_solr_hdfs_support
from setup_solr_kerberos_auth import setup_solr_kerberos_auth, remove_solr_kerberos_auth
from setup_solr_ssl_support import setup_solr_ssl_support, remove_solr_ssl_support
from solr_utils import is_solr_running, solr_port_validation, delete_write_lock_files


class Solr(Script):
    def install(self, env):
        import params
        env.set_params(params)
        self.install_packages(env)

    def configure(self, env):
        import params
        env.set_params(params)
        setup_solr()

        if params.solr_cloud_mode:
            setup_solr_cloud()

        if params.solr_hdfs_enable:
            setup_solr_hdfs_support()

        if params.solr_ssl_enable:
            setup_solr_ssl_support()
        else:
            remove_solr_ssl_support()

        if params.security_enabled:
            setup_solr_kerberos_auth()
        else:
            remove_solr_kerberos_auth()

        if params.solr_hdfs_enable and params.solr_hdfs_delete_write_lock_files:
            delete_write_lock_files()


    def start(self, env):
        import params
        env.set_params(params)
        self.configure(env)

        if not solr_port_validation():
            exit(1)

        if is_solr_running():
            Logger.info("Solr is running, it can not be started it again")
            exit(1)

        Logger.info("Starting Solr ... ")
        start_command = format('{solr_config_bin_dir}/solr start >> {solr_config_service_log_file} 2>&1')

        Execute(
            start_command,
            environment={'JAVA_HOME': params.java64_home},
            user=params.solr_config_user
        )

    def stop(self, env):
        import params
        env.set_params(params)


        if not is_solr_running():
            Logger.info("Solr is not running, it can not be stopped it again")
            return

        Execute(
            format(
                '{solr_config_bin_dir}/solr stop -all >> {solr_config_service_log_file} 2>&1'),
            environment={'JAVA_HOME': params.java64_home},
            user=params.solr_config_user
        )

        File(
            params.solr_config_pid_file,
            action="delete"
        )

    def status(self, env):
        import status_params
        env.set_params(status_params)

        check_process_status(status_params.solr_config_pid_file)


if __name__ == "__main__":
    Solr().execute()
