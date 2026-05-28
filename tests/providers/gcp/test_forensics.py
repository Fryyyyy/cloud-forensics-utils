# -*- coding: utf-8 -*-
# Copyright 2020 Google Inc.
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
"""Tests for the gcp module - forensics.py"""

import typing
import unittest
import mock

from libcloudforensics import errors
from libcloudforensics.providers.gcp import forensics
from libcloudforensics.providers.gcp.internal import compute

from tests.providers.gcp import gcp_mocks


class GCPForensicsTest(unittest.TestCase):
  """Test forensics.py methods and common.py helper methods."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testCreateDiskCopy1(self,
                          mock_gce_api,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_block_operation,
                          mock_disk_type):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = gcp_mocks.MOCK_INSTANCES_AGGREGATED
    mock_get_instance.return_value = gcp_mocks.FAKE_INSTANCE
    mock_get_boot_disk.return_value = gcp_mocks.FAKE_BOOT_DISK
    mock_block_operation.return_value = None
    mock_disk_type.return_value = 'fake-disk-type'

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     zone='fake-zone',
    #     instance_name='fake-instance',
    #     disk_name=None) Should grab the boot disk
    new_disk = forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                                        gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                                        zone=gcp_mocks.FAKE_INSTANCE.zone,
                                        instance_name=gcp_mocks.FAKE_INSTANCE.name)
    mock_get_instance.assert_called_with(gcp_mocks.FAKE_INSTANCE.name, zone=None)
    mock_get_disk.assert_not_called()
    self.assertIsInstance(new_disk, compute.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertIn('fake-boot-disk', new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testCreateDiskCopy2(self,
                          mock_gce_api,
                          mock_get_disk,
                          mock_get_boot_disk,
                          mock_block_operation,
                          mock_disk_type):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = gcp_mocks.MOCK_INSTANCES_AGGREGATED
    mock_get_disk.return_value = gcp_mocks.FAKE_DISK
    mock_block_operation.return_value = None
    mock_disk_type.return_value = 'fake-disk-type'

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     zone='fake-zone',
    #     instance_name=None,
    #     disk_name='fake-disk') Should grab 'fake-disk'
    new_disk = forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                                        gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                                        zone=gcp_mocks.FAKE_INSTANCE.zone,
                                        disk_name=gcp_mocks.FAKE_DISK.name)
    mock_get_disk.assert_called_with(gcp_mocks.FAKE_DISK.name, zone=None)
    mock_get_boot_disk.assert_not_called()
    self.assertIsInstance(new_disk, compute.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertIn('fake-disk', new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListInstances')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  def testCreateDiskCopy3(self, mock_list_disks, mock_list_instances,
                          mock_get_disk, mock_get_instance):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    mock_list_disks.return_value = gcp_mocks.MOCK_LIST_DISKS
    mock_list_instances.return_value = gcp_mocks.MOCK_LIST_INSTANCES
    mock_get_disk.side_effect = errors.ResourceNotFoundError(
        'Disk not found', __name__)
    mock_get_instance.side_effect = errors.ResourceNotFoundError(
        'Instance not found', __name__)

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     zone='fake-zone',
    #     instance_name=None,
    #     disk_name='non-existent-disk') Should raise an exception
    with self.assertRaises(errors.ResourceNotFoundError):
      forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                               gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                               zone=gcp_mocks.FAKE_INSTANCE.zone,
                               disk_name='non-existent-disk')

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     instance_name='non-existent-instance',
    #     zone='fake-zone',
    #     disk_name=None) Should raise an exception
    with self.assertRaises(errors.ResourceNotFoundError):
      forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                               gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                               instance_name='non-existent-instance',
                               zone=gcp_mocks.FAKE_INSTANCE.zone, disk_name='')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  @mock.patch('subprocess.run')
  def testCheckInstanceSSHAuth(self, mock_subprocess, mock_project):
    """Test that ssh authentication options are properly parsed."""
    mock_instance =  mock_project.return_value.compute.GetInstance.return_value
    mock_instance.GetOperation.return_value = (
        gcp_mocks.MOCK_GCE_OPERATION_INSTANCES_GET)
    mock_instance.GetNatIps.return_value = ['0.0.0.0']
    mock_subprocess.return_value.stderr = gcp_mocks.MOCK_SSH_VERBOSE_STDERR
    ssh_auth = forensics.CheckInstanceSSHAuth(
        'fake_project' , 'fake_instance')
    self.assertListEqual(
        ssh_auth, ['publickey', 'password', 'keyboard-interactive'])

  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testCopyDisksToGCS(self, mock_project: mock.MagicMock) -> None:
    """Tests copying a disk to GCS storage."""

    dest_bucket_name = gcp_mocks.MOCK_GCS_BUCKETS['items'][0].get('name')  # type: ignore

    forensics.CopyDisksToGCS(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                             gcp_mocks.FAKE_DISK.name,
                             dest_bucket_name,
                             '/path/to/directory/',
                             'qcow2')

    mock_project.assert_called_once_with(gcp_mocks.FAKE_SOURCE_PROJECT.project_id)
    mock_project.return_value.compute.GetDisk.assert_called_once_with(gcp_mocks.FAKE_DISK.name)

    mock_disk_obj = mock_project.return_value.compute.GetDisk.return_value
    mock_project.return_value.compute.CreateImageFromDisk.assert_called_once_with(mock_disk_obj)

    mock_image_obj = mock_project.return_value.compute.CreateImageFromDisk.return_value
    mock_image_obj.ExportImage.assert_called_once_with(
        gcs_output_folder=f'gs://{dest_bucket_name}/{"/path/to/directory/"}',
        image_format='qcow2',
        output_name=mock_disk_obj.name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.InsertFirewallRule')
  def testMIGNetworkQuarantine_WithParams(self, mock_insert_firewall):
    """Test MIGNetworkQuarantine when parameters are provided directly."""
    mock_insert_firewall.return_value = None

    rule_names = forensics.MIGNetworkQuarantine(
        'fake-project-id',
        'fake-mig',
        'fake-zone',
        network='fake-network',
        target_tags=['tag1'],
        target_sas=['sa1@google.com']
    )

    self.assertEqual(len(rule_names), 2)
    self.assertTrue(rule_names[0].startswith('quarantine-mig-fake-mig-'))
    self.assertTrue(rule_names[0].endswith('-ingress'))
    self.assertTrue(rule_names[1].endswith('-egress'))

    self.assertEqual(mock_insert_firewall.call_count, 2)

    calls = mock_insert_firewall.call_args_list
    ingress_body = calls[0].kwargs['body']
    egress_body = calls[1].kwargs['body']

    self.assertEqual(ingress_body['direction'], 'INGRESS')
    self.assertEqual(egress_body['direction'], 'EGRESS')
    self.assertEqual(ingress_body['network'], 'fake-network')
    self.assertEqual(ingress_body['targetTags'], ['tag1'])
    self.assertEqual(ingress_body['targetServiceAccounts'], ['sa1@google.com'])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.InsertFirewallRule')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testMigNetworkQuarantine_FetchTemplate(self, mock_gce_api, mock_insert_firewall):
    """Test MigNetworkQuarantine when it needs to fetch the template."""
    mock_insert_firewall.return_value = None

    gce_api = mock_gce_api.return_value

    # Mock IGM get
    mock_igm = {
        'instanceTemplate': 'https://.../templates/fake-template'
    }
    gce_api.instanceGroupManagers.return_value.get.return_value.execute.return_value = mock_igm

    # Mock Template get
    mock_template = {
        'properties': {
            'networkInterfaces': [{'network': 'fake-network-from-template'}],
            'tags': {'items': ['tag-from-template']},
            'serviceAccounts': [{'email': 'sa-from-template@google.com'}]
        }
    }
    gce_api.instanceTemplates.return_value.get.return_value.execute.return_value = mock_template

    rule_names = forensics.MIGNetworkQuarantine(
        'fake-project-id',
        'fake-mig',
        'fake-zone'
    )

    self.assertEqual(len(rule_names), 2)
    self.assertEqual(mock_insert_firewall.call_count, 2)

    calls = mock_insert_firewall.call_args_list
    ingress_body = calls[0].kwargs['body']

    self.assertEqual(ingress_body['network'], 'fake-network-from-template')
    self.assertEqual(ingress_body['targetTags'], ['tag-from-template'])
    self.assertEqual(ingress_body['targetServiceAccounts'], ['sa-from-template@google.com'])
