"""
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

"""
import glob
import os
import shutil
import tempfile

from resource_management.core import shell
from resource_management.core.logger import Logger
from resource_management.core.exceptions import Fail
from resource_management.core.resources.system import Execute
from resource_management.core.resources.system import Directory
from resource_management.core.resources.system import File
from resource_management.libraries.functions import Direction
from resource_management.libraries.functions import format
from resource_management.libraries.functions import compare_versions
from resource_management.libraries.functions import tar_archive
from resource_management.libraries.script.script import Script

import oozie

BACKUP_TEMP_DIR = "oozie-upgrade-backup"
BACKUP_CONF_ARCHIVE = "oozie-conf-backup.tar"

class OozieUpgrade(Script):

  @staticmethod
  def backup_configuration():
    """
    Backs up the oozie configuration as part of the upgrade process.
    :return:
    """
    Logger.info('Backing up Oozie configuration directory before upgrade...')
    directoryMappings = OozieUpgrade._get_directory_mappings()

    absolute_backup_dir = os.path.join(tempfile.gettempdir(), BACKUP_TEMP_DIR)
    if not os.path.isdir(absolute_backup_dir):
      os.makedirs(absolute_backup_dir)

    for directory in directoryMappings:
      if not os.path.isdir(directory):
        raise Fail("Unable to backup missing directory {0}".format(directory))

      archive = os.path.join(absolute_backup_dir, directoryMappings[directory])
      Logger.info('Compressing {0} to {1}'.format(directory, archive))

      if os.path.exists(archive):
        os.remove(archive)

      # backup the directory, following symlinks instead of including them
      tar_archive.archive_directory_dereference(archive, directory)


  @staticmethod
  def restore_configuration():
    """
    Restores the configuration backups to their proper locations after an
    upgrade has completed.
    :return:
    """
    Logger.info('Restoring Oozie configuration directory after upgrade...')
    directoryMappings = OozieUpgrade._get_directory_mappings()

    for directory in directoryMappings:
      archive = os.path.join(tempfile.gettempdir(), BACKUP_TEMP_DIR,
        directoryMappings[directory])

      if not os.path.isfile(archive):
        raise Fail("Unable to restore missing backup archive {0}".format(archive))

      Logger.info('Extracting {0} to {1}'.format(archive, directory))

      tar_archive.untar_archive(archive, directory)

    # cleanup
    Directory(os.path.join(tempfile.gettempdir(), BACKUP_TEMP_DIR),
              action="delete",
    )

  @staticmethod
  def prepare_warfile():
    """
    Invokes the 'prepare-war' command in Oozie in order to create the WAR.
    The prepare-war command uses the input WAR from ${OOZIE_HOME}/oozie.war and
    outputs the prepared WAR to ${CATALINA_BASE}/webapps/oozie.war - because of this,
    both of these environment variables must point to the upgraded oozie-server path and
    not oozie-client since it was not yet updated.

    This method will also perform a kinit if necessary.
    :return:
    """
    import params

    # get the kerberos token if necessary to execute commands as oozie
    if params.security_enabled:
      oozie_principal_with_host = params.oozie_principal.replace("_HOST", params.hostname)
      command = format("{kinit_path_local} -kt {oozie_keytab} {oozie_principal_with_host}")
      Execute(command, user=params.oozie_user, logoutput=True)

    # setup environment
    environment = { "CATALINA_BASE" : "/usr/hdp/current/oozie-server/oozie-server",
      "OOZIE_HOME" : "/usr/hdp/current/oozie-server" }

    # prepare the oozie WAR
    command = format("{oozie_setup_sh} prepare-war {oozie_secure} -d {oozie_libext_dir}")
    return_code, oozie_output = shell.call(command, user=params.oozie_user,
      logoutput=False, quiet=False, env=environment)

    # set it to "" in to prevent a possible iteration issue
    if oozie_output is None:
      oozie_output = ""

    if return_code != 0 or "New Oozie WAR file with added".lower() not in oozie_output.lower():
      message = "Unexpected Oozie WAR preparation output {0}".format(oozie_output)
      Logger.error(message)
      raise Fail(message)

  @staticmethod
  def _get_directory_mappings():
    """
    Gets a dictionary of directory to archive name that represents the
    directories that need to be backed up and their output tarball archive targets
    :return:  the dictionary of directory to tarball mappings
    """
    import params

    # the trailing "/" is important here so as to not include the "conf" folder itself
    return { params.conf_dir + "/" : BACKUP_CONF_ARCHIVE }


if __name__ == "__main__":
  OozieUpgrade().execute()
