# -*- coding: utf-8 -*-
# Copyright 2026 Google Inc.
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
"""Tests for the gcp module - tpu.py"""

import typing
import unittest
import mock
from googleapiclient.errors import HttpError

from libcloudforensics import errors
from libcloudforensics.providers.gcp.internal import tpu as gcp_tpu
from libcloudforensics.providers.gcp.internal import compute as compute_module
from tests.providers.gcp import gcp_mocks


class GoogleCloudTpuTest(unittest.TestCase):
  """Test Google Cloud TPU class."""

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.tpu.GoogleCloudTPU.TPUApi')
  def testGetNode(self, mock_tpu_api):
    """Test GetNode operation."""
    nodes = mock_tpu_api.return_value.projects.return_value.locations.return_value.nodes
    nodes.return_value.get.return_value.execute.return_value = gcp_mocks.MOCK_TPU_NODE

    tpu_node = gcp_mocks.FAKE_TPU.GetNode('fake-tpu', 'fake-zone')
    self.assertIsInstance(tpu_node, gcp_tpu.GoogleCloudTPUNode)
    self.assertEqual('fake-tpu', tpu_node.name)
    self.assertEqual('fake-zone', tpu_node.location)
    self.assertEqual({'key': 'value'}, tpu_node.labels)

    # Test HttpError 404
    nodes.return_value.get.return_value.execute.side_effect = HttpError(
        resp=mock.MagicMock(status=404), content=b'Not Found')
    with self.assertRaises(errors.ResourceNotFoundError):
      gcp_mocks.FAKE_TPU.GetNode('fake-tpu', 'fake-zone')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.ExecuteRequest')
  @mock.patch('libcloudforensics.providers.gcp.internal.tpu.GoogleCloudTPU.TpuApi')
  def testListNodes(self, mock_tpu_api, mock_execute_request):
    """Test ListNodes operation."""
    nodes = mock_tpu_api.return_value.projects.return_value.locations.return_value.nodes
    mock_execute_request.return_value = [gcp_mocks.MOCK_TPU_NODES_LIST]

    tpu_nodes = gcp_mocks.FAKE_TPU.ListNodes('fake-zone')
    self.assertEqual(1, len(tpu_nodes))
    self.assertEqual('fake-tpu', tpu_nodes[0].name)
    mock_execute_request.assert_called_with(
        nodes.return_value, 'list',
        {'parent': 'projects/fake-target-project/locations/fake-zone'})

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.ExecuteRequest')
  @mock.patch('libcloudforensics.providers.gcp.internal.tpu.GoogleCloudTPU.TPUApi')
  def testListLocations(self, mock_tpu_api, mock_execute_request):
    """Test ListLocations operation."""
    locations = mock_tpu_api.return_value.projects.return_value.locations
    mock_execute_request.return_value = [gcp_mocks.MOCK_TPU_LOCATIONS]

    locs = gcp_mocks.FAKE_TPU.ListLocations()
    self.assertEqual(1, len(locs))
    self.assertEqual('fake-zone', locs[0])
    mock_execute_request.assert_called_with(
        locations.return_value, 'list',
        {'name': 'projects/fake-target-project'})

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.tpu.GoogleCloudTPU.ListLocations')
  @mock.patch('libcloudforensics.providers.gcp.internal.tpu.GoogleCloudTPU.GetNode')
  def testFindNode(self, mock_get_node, mock_list_locations):
    """Test FindNode operation."""
    mock_list_locations.return_value = ['zone-1', 'zone-2']
    mock_get_node.side_effect = [
        errors.ResourceNotFoundError('Not found', 'name'),
        gcp_tpu.GoogleCloudTPUNode('fake-project', 'zone-2', 'fake-tpu', gcp_mocks.MOCK_TPU_NODE)
    ]

    node = gcp_mocks.FAKE_TPU.FindNode('fake-tpu')
    self.assertEqual('zone-2', node.location)
    self.assertEqual(2, mock_get_node.call_count)

    # Test not found in any location
    mock_get_node.side_effect = [
        errors.ResourceNotFoundError('Not found', 'name'),
        errors.ResourceNotFoundError('Not found', 'name')
    ]
    with self.assertRaises(errors.ResourceNotFoundError):
      gcp_mocks.FAKE_TPU.FindNode('fake-tpu')


class GoogleCloudTpuNodeTest(unittest.TestCase):
  """Test Google Cloud TPU Node class."""

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  def testGetBootDisk(self, mock_get_disk):
    """Test GetBootDisk operation."""
    node = gcp_tpu.GoogleCloudTPUNode(
        'fake-project', 'fake-zone', 'fake-tpu', gcp_mocks.MOCK_TPU_NODE)
    mock_get_disk.return_value = gcp_mocks.FAKE_BOOT_DISK

    boot_disk = node.GetBootDisk()
    self.assertIsInstance(boot_disk, compute_module.GoogleComputeDisk)
    self.assertEqual('fake-boot-disk', boot_disk.name)
    mock_get_disk.assert_called_with(
        disk_name='fake-tpu-boot-disk', zone='fake-zone')

    # Test no boot disk in node dict
    node_no_boot = gcp_tpu.GoogleCloudTPUNode(
        'fake-project', 'fake-zone', 'fake-tpu', {'name': 'fake-tpu'})
    self.assertIsNone(node_no_boot.GetBootDisk())

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  def testListDisks(self, mock_get_disk):
    """Test ListDisks operation."""
    node = gcp_tpu.GoogleCloudTPUNode(
        'fake-project', 'fake-zone', 'fake-tpu', gcp_mocks.MOCK_TPU_NODE)
    mock_get_disk.return_value = gcp_mocks.FAKE_DISK

    disks = node.ListDisks()
    self.assertEqual(1, len(disks))
    self.assertIn('fake-tpu-data-disk', disks)
    self.assertIsInstance(disks['fake-tpu-data-disk'], compute_module.GoogleComputeDisk)
    mock_get_disk.assert_called_with(
        disk_name='fake-tpu-data-disk', zone='fake-zone')
