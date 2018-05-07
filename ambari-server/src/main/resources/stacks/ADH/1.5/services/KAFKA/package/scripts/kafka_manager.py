from resource_management import *

class kafka_manager(Script):
    def install(self, env):
        Logger.info("Installing Kafka Manager packages")
        self.install_packages(env)
        #if any other install steps were needed they can be added here

    def configure(self,env):
        import params
        env.set_params(params)
        File(format("{kafka_manager_conf_dir}/kafka-manager-env"),
        mode=0755,
        content = InlineTemplate(params.kafka_manager_env_content)
        )
        File(format("{kafka_manager_conf_dir}/application.conf"),
        mode=0755,
        content = InlineTemplate(params.kafka_manager_application_conf_content)
        )


    #To stop the service, use the linux service stop command and pipe output to log file
    def stop(self, env):
        Logger.info("Stopping Kafka Manager service")
        Execute('service kafka-manager stop')

    #To start the service, use the linux service start command and pipe output to log file
    def start(self, env):
        import params
        env.set_params(params)
        self.configure(env)
        Logger.info("Starting Kafka Manager service")
        Execute('service kafka-manager start')

    #To get status of the, use the linux service status command
    def status(self, env):
        Logger.info("Getting status of Kafka Manager service")
        try:
            Execute('service kafka-manager status')
        except Fail:
            raise ComponentIsNotRunning()

if __name__ == "__main__":
    kafka_manager().execute()

