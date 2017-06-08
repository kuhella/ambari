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

import os
from resource_management import *
from ambari_commons import OSConst
from ambari_commons.os_family_impl import OsFamilyFuncImpl, OsFamilyImpl

@OsFamilyFuncImpl(os_family=OsFamilyImpl.DEFAULT)
def hst(type=None, rolling_restart=False):
  import params

  Directory(params.hst_conf_dir, recursive=True)

  if (params.log4j_props != None):
    File(format("{params.hst_conf_dir}/log4j.properties"),
      mode=0644,
      content=params.log4j_props
    )

@OsFamilyFuncImpl(os_family=OSConst.WINSRV_FAMILY)
def hst(type=None, rolling_restart=False):
  import params
  if (params.log4j_props != None):
    File(os.path.join(params.hst_conf_dir, "log4j.properties"),
         mode='f',
         content=params.log4j_props
    )
