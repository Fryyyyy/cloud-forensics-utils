# -*- coding: utf-8 -*-
# Copyright 2021 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Google Cloud Storage Transfer functionalities."""

from typing import TYPE_CHECKING, Dict, Any, Optional
import datetime

from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import storage as gcp_storage

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudStorageTransfer:
  """Class to call Google Cloud Storage Transfer APIs.

  Attributes:
    gcst_api_client: Client to interact with GCST APIs.
    project_id: Google Cloud project ID.
  """
  CLOUD_STORAGE_TRANSFER_API_VERSION = 'v1'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleCloudStorageTransfer object.

    Args:
      project_id (str): Optional. Google Cloud project ID.
    """

    self.gcst_api_client = None
    self.project_id = project_id

  def GcstApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Storage Transfer service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Storage Transfer
        service object.
    """

    if self.gcst_api_client:
      return self.gcst_api_client
    self.gcst_api_client = common.CreateService(
        'storagetransfer', self.CLOUD_STORAGE_TRANSFER_API_VERSION)
    return self.gcst_api_client

  def S3ToGCS(self,
              s3_path: str,
              zone: str,
              gcs_path: str) -> Dict[str, Any]:
    """Copy an S3 object to a GCS bucket.

    Args:
      s3_path (str): File path to the S3 resource.
          Ex: s3://test/bucket/obj
      zone (str): The AWS zone in which resources are located.
        Available zones are listed at:
        https://cloud.google.com/storage-transfer/docs/create-manage-transfer-program#s3-to-cloud  # pylint: disable=line-too-long
      gcs_path (str): File path to the target GCS bucket.
          Ex: gs://bucket/folder

    Returns:
      Dict: An API operation object for a Google Cloud Storage Transfer job.
        https://cloud.google.com/storage-transfer/docs/reference/rest/v1/transferJobs#TransferJob  # pylint: disable=line-too-long
    """
    aws_creds = account.AWSAccount(zone).session.get_credentials()
    s3_bucket, s3_path = gcp_storage.SplitStoragePath(s3_path)
    gcs_bucket, gcs_path = gcp_storage.SplitStoragePath(gcs_path)
    today = datetime.datetime.now()
    transfer_job_body = {
        'projectId': self.project_id,
        'description': 'created_by_cfu',
        'transferSpec': {
            'objectConditions': {
                'includePrefixes': [s3_path]
            },
            'awsS3DataSource': {
                'bucketName': s3_bucket,
                'awsAccessKey': {
                    'accessKeyId': aws_creds.access_key,
                    'secretAccessKey': aws_creds.secret_key
                }
            },
            'gcsDataSink': {
                'bucketName': gcs_bucket, 'path': gcs_path
            }
        },
        'schedule': {
            'scheduleStartDate': {
                'year': today.year, 'month': today.month, 'day': today.day
            },
            'scheduleEndDate': {
                'year': today.year, 'month': today.month, 'day': today.day
            },
            'endTimeOfDay': {}
        },
        'status': 'ENABLED'
    }
    logger.info(
        'Creating transfer job with spec: {0:s}'.format(str(transfer_job_body)))
    gcst_jobs = self.GcstApi().transferJobs()
    create_request = gcst_jobs.create(body=transfer_job_body)
    return create_request.execute()
