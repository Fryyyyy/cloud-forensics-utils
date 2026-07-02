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
"""Google Cloud TPU Node resources and services."""

from typing import Any, Dict, List, Optional
from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import compute as compute_module
from libcloudforensics import errors
from libcloudforensics import logging_utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class GoogleCloudTPUNode:
  """Class representing a Google Cloud TPU Node.

  Attributes:
    project_id (str): Google Cloud project ID.
    location (str): What location (zone) the resource is in.
    name (str): Name of the resource.
  """

  def __init__(self,
               project_id: str,
               location: str,
               name: str,
               node_dict: Dict[str, Any]) -> None:
    """Initialize the Google Cloud TPU Node object.

    Args:
      project_id: Google Cloud project ID.
      location: What location (zone) the resource is in.
      name: Name of the resource.
      node_dict: Dictionary containing the TPU node resource data.
    """
    self.project_id = project_id
    self.location = location
    self.name = name
    self._node_dict = node_dict

  @property
  def labels(self) -> Dict[str, str]:
    """Get the labels of the TPU node."""
    return self._node_dict.get('labels', {})

  def GetBootDisk(self) -> Optional[compute_module.GoogleComputeDisk]:
    """Get the TPU boot disk if available.

    Returns:
      GoogleComputeDisk: Disk object if found, None otherwise.
    """
    boot_disk_dict = self._node_dict.get('bootDisk')
    if not boot_disk_dict:
      return None
    source_disk = boot_disk_dict.get('sourceDisk')
    if not source_disk:
      return None
    # Parse projects/{project}/zones/{zone}/disks/{disk}
    parts = source_disk.split('/')
    try:
      disk_project = parts[1]
      disk_zone = parts[3]
      disk_name = parts[5]
      return compute_module.GoogleCloudCompute(disk_project).GetDisk(
          disk_name=disk_name, zone=disk_zone)
    except IndexError:
      logger.warning(f'Could not parse boot disk source: {source_disk}')
      return None

  def ListDisks(self) -> Dict[str, compute_module.GoogleComputeDisk]:
    """List all data disks for the TPU node.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disk names to their
          respective GoogleComputeDisk object.
    """
    disks = {}
    data_disks = self._node_dict.get('dataDisks', [])
    for disk_dict in data_disks:
      source_disk = disk_dict.get('sourceDisk')
      if not source_disk:
        continue
      parts = source_disk.split('/')
      try:
        disk_project = parts[1]
        disk_zone = parts[3]
        disk_name = parts[5]
        disks[disk_name] = compute_module.GoogleCloudCompute(
            disk_project
        ).GetDisk(disk_name=disk_name, zone=disk_zone)
      except IndexError:
        logger.warning(f'Could not parse data disk source: {source_disk}')
        continue
    return disks


class GoogleCloudTPU:
  """Class representing all Google Cloud TPU objects in a project.

  Attributes:
    project_id: Project name.
  """

  TPU_API_VERSION = 'v2'

  def __init__(self, project_id: str) -> None:
    """Initialize the Google Cloud TPU service.

    Args:
      project_id (str): Google Cloud project ID.
    """
    self.project_id = project_id
    self._tpu_api_client = None

  def TPUApi(self) -> Any:
    """Get a Google Cloud TPU service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud TPU service object.
    """
    if self._tpu_api_client:
      return self._tpu_api_client
    self._tpu_api_client = common.CreateService(
        'tpu', self.TPU_API_VERSION)
    return self._tpu_api_client

  def GetNode(self, node_name: str, location: str) -> GoogleCloudTPUNode:
    """Get a TPU node.

    Args:
      node_name: The name of the TPU node.
      location: The location (zone) of the TPU node.

    Returns:
      GoogleCloudTPUNode: A Google Cloud TPU Node object.

    Raises:
      ResourceNotFoundError: If the TPU node does not exist.
    """
    client = self.TPUApi().projects().locations().nodes() # pylint: disable=no-member
    name = f'projects/{self.project_id}/locations/{location}/nodes/{node_name}'
    try:
      node_dict = client.get(name=name).execute()
      return GoogleCloudTPUNode(self.project_id, location, node_name, node_dict)
    except HttpError as e:
      if e.resp.status == 404:
        raise errors.ResourceNotFoundError(
            f'TPU Node {node_name} was not found in project {self.project_id} '
            f'location {location}',
            __name__) from e
      raise

  def ListNodes(self, location: str) -> List[GoogleCloudTPUNode]:
    """List TPU nodes in a location.

    Args:
      location: The location (zone) to list nodes in.

    Returns:
      List[GoogleCloudTPUNode]: A list of TPU Node objects.
    """
    client = self.TPUApi().projects().locations().nodes() # pylint: disable=no-member
    parent = f'projects/{self.project_id}/locations/{location}'
    try:
      responses = common.ExecuteRequest(
          client, 'list', {'parent': parent})
      nodes = []
      for response in responses:
        for node_dict in response.get('nodes', []):
          node_name = node_dict['name'].split('/')[-1]
          nodes.append(GoogleCloudTPUNode(
              self.project_id, location, node_name, node_dict))
      return nodes
    except HttpError as e:
      logger.warning(f'Failed to list nodes in {location}: {e}')
      return []

  def ListLocations(self) -> List[str]:
    """List available locations for TPUs.

    Returns:
      List[str]: A list of location IDs.
    """
    client = self.TPUApi().projects().locations() # pylint: disable=no-member
    name = f'projects/{self.project_id}'
    try:
      responses = common.ExecuteRequest(client, 'list', {'name': name})
      locations = []
      for response in responses:
        for loc in response.get('locations', []):
          locations.append(loc['locationId'])
      return locations
    except HttpError as e:
      logger.error(f'Failed to list locations: {e}')
      raise

  def FindNode(self, node_name: str, location: Optional[str] = None) -> GoogleCloudTPUNode:
    """Find a TPU node by name, optionally specifying location.

    Args:
      node_name: The name of the TPU node.
      location: Optional location. If not specified, all locations are searched.

    Returns:
      GoogleCloudTPUNode: A Google Cloud TPU Node object.

    Raises:
      ResourceNotFoundError: If the TPU node is not found.
    """
    if location:
      return self.GetNode(node_name, location)

    locations = self.ListLocations()
    for loc in locations:
      try:
        return self.GetNode(node_name, loc)
      except errors.ResourceNotFoundError:
        continue
    raise errors.ResourceNotFoundError(
        f'TPU Node {node_name} was not found in any location in project {self.project_id}',
        __name__)
