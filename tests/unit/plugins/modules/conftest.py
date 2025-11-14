#!/usr/bin/python

# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansibleモジュールテスト用の共有fixture"""

import pytest


@pytest.fixture
def raidadapter_profile_response():
    """RAIDAdapterProfile APIレスポンス全体（実機データ）

    データソース:
    - API: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
    - 構成: RAIDAdapter 1台、LogicalDrive 1個（RAID0）、PhysicalDisk 1台（SATA SSD）

    このfixtureは実機から取得した完全なAPIレスポンスを保持しており、
    各テストでは必要な部分を抽出して使用します。
    """
    return {
        "Server": {
            "HWConfigurationIrmc": {
                "Adapters": {
                    "RAIDAdapter": [
                        {
                            "@AdapterId": "RAIDAdapter0",
                            "@ConfigurationType": "Addressing",
                            "PCIId": {
                                "Vendor": "1000",
                                "Device": "10E2",
                                "ControllerIndex": 0
                            },
                            "Features": {
                                "RaidLevel": "0,1,5,6,1E,10,50,60",
                                "Stripe": {
                                    "@Unit": "KB",
                                    "#text": "64,128,256,512,1024"
                                },
                                "InitMode": "no,fast,slow",
                                "WriteMode": "WriteBack,WriteThrough,AlwaysWriteBack",
                                "ReadMode": "NoReadAhead,ReadAhead",
                                "CacheMode": "Direct,Cached",
                                "DiskCacheMode": "Enabled,Disabled,Unchanged"
                            },
                            "BGIRate": 30,
                            "MDCRate": 30,
                            "RebuildRate": 30,
                            "EnableCopyback": "Enabled",
                            "EnableCopybackOnSMART": "Enabled",
                            "EnableCopybackOnSSDSMART": "Enabled",
                            "AutoRebuild": "Enabled",
                            "Arrays": {
                                "Array": [
                                    {
                                        "@Number": 0,
                                        "@ConfigurationType": "Addressing",
                                        "PhysicalDiskRefs": {
                                            "PhysicalDiskRef": [
                                                {
                                                    "@Number": "0"
                                                }
                                            ]
                                        }
                                    }
                                ]
                            },
                            "LogicalDrives": {
                                "LogicalDrive": [
                                    {
                                        "@Number": 239,
                                        "@Action": "None",
                                        "RaidLevel": "0",
                                        "ArrayRefs": {
                                            "ArrayRef": [
                                                {
                                                    "@Number": 0
                                                }
                                            ]
                                        },
                                        "WriteMode": "WriteThrough",
                                        "ReadMode": "ReadAhead",
                                        "CacheMode": "Direct",
                                        "DiskCacheMode": "Disabled",
                                        "Stripe": {
                                            "@Unit": "KB",
                                            "#text": 256
                                        },
                                        "InitMode": "no",
                                        "LDStatus": "Operational",
                                        "Name": "LogicalDrive_0",
                                        "Size": {
                                            "@Unit": "GB",
                                            "#text": 446
                                        }
                                    }
                                ]
                            },
                            "PhysicalDisks": {
                                "PhysicalDisk": [
                                    {
                                        "@Number": "0",
                                        "@Action": "None",
                                        "Slot": 0,
                                        "PDStatus": "Operational",
                                        "Interface": "SATA",
                                        "Type": "SSD",
                                        "Vendor": "ATA",
                                        "Product": "SAMSUNG MZ7L348",
                                        "Size": {
                                            "@Unit": "GB",
                                            "#text": 447
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                },
                "@Version": "1.00"
            },
            "@Version": "1.01"
        }
    }


@pytest.fixture
def storage_response():
    """Storage APIレスポンス全体（実機データ）

    データソース:
    - API: GET /redfish/v1/Systems/0/Storage?$expand=Members
    - 構成: Storage 2台（PRAID EP640i + Windows AHCI）

    このfixtureは実機から取得した完全なAPIレスポンスを保持しており、
    各テストでは必要な部分を抽出して使用します。
    """
    return {
        "@odata.id": "/redfish/v1/Systems/0/Storage",
        "@odata.type": "#StorageCollection.StorageCollection",
        "Name": "Storage Collection",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Systems/0/Storage/0",
                "@odata.type": "#Storage.v1_7_2.Storage",
                "Oem": {
                },
                "Id": "0",
                "Name": "PRAID EP640i (1)",
                "Links": {
                    "Oem": {
                    },
                    "Enclosures": [
                        {
                            "@odata.id": "/redfish/v1/Systems/0/Storage/0/Enclosures/0"
                        }
                    ],
                    "Enclosures@odata.count": 1
                },
                "Actions": {
                    "Oem": {
                        "#FTSStorage.CreateVolumes": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.CreateVolumes",
                            "title": "Create volumes for this controller"
                        },
                        "#FTSStorage.DeleteVolumes": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.DeleteVolumes",
                            "title": "Delete volumes from this controller"
                        },
                        "#FTSStorage.DeleteAllVolumes": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.DeleteAllVolumes",
                            "title": "Delete all volumes from this controller",
                            "Command@Redfish.AllowableValues": [
                                "All"
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/0/Oem/ts_fujitsu/FTSStorageDeleteAllVolumesActionInfo"
                        },
                        "#FTSStorage.Reload": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.Reload",
                            "title": "Relaod storage data from this controller"
                        },
                        "#FTSStorage.PatrolRead": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.PatrolRead",
                            "title": "Control Patrol Read operation for this controller",
                            "Command@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/0/Oem/ts_fujitsu/FTSStoragePatrolReadActionInfo"
                        },
                        "#FTSStorage.ForeignConfiguration": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.ForeignConfiguration",
                            "title": "Manage foreign configuration on this controller",
                            "Command@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/0/Oem/ts_fujitsu/FTSStorageForeignConfigurationActionInfo"
                        },
                        "#FTSStorage.ClearConfiguration": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.ClearConfiguration",
                            "title": "Clear configuration of this controller",
                            "Command@Redfish.AllowableValues": [
                                "Clear"
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/0/Oem/ts_fujitsu/FTSStorageClearConfigurationActionInfo"
                        },
                        "#FTSStorage.ClearPreservedCache": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.ClearPreservedCache",
                            "title": "Clear Preserved Cache data of this controller"
                        },
                        "#FTSStorage.ManageSchedule": {
                            "target": "/redfish/v1/Systems/0/Storage/0/Actions/Oem/FTSStorage.ManageSchedule",
                            "title": "Manage Schedule",
                            "Name@Redfish.AllowableValues": [
                                "StartMDC",
                                "StartPatrolRead"
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/0/Oem/ts_fujitsu/FTSStorageManageScheduleActionInfo"
                        }
                    }
                },
                "Status": {
                    "State": "Enabled",
                    "Health": "OK",
                    "HealthRollup": "OK",
                    "Oem": {
                    }
                },
                "StorageControllers@odata.count": 1,
                "StorageControllers": [
                    {
                        "Oem": {
                            "ts_fujitsu": {
                                "@odata.type": "#FTSStorageController.v3_6_0.FTSStorageController",
                                "ControllerNumber": 538,
                                "VendorId": 4096,
                                "DeviceId": 4322,
                                "SubsystemVendorId": 4303,
                                "SubsystemId": 6612,
                                "FirmwarePackageVersion": "52.26.0-5122",
                                "FirmwareBuildDate": "2023-09-08T14:29:17+00:00",
                                "BiosVersion": "7.26.00.0",
                                "BiosBuildDate": "2023-07-12",
                                "MemorySizeMiB": 4096,
                                "FlashRomSizeMiB": 16,
                                "NvramSizeKiB": 128,
                                "ChipTemperatureC": 58,
                                "PortCount": 8,
                                "PCISegmentNumber": 0,
                                "PCIBusNumber": 2,
                                "PCIDeviceNumber": 0,
                                "PCIFunctionNumber": 0,
                                "DriverName": "megasas",
                                "DriverVersion": "7.732.03.00",
                                "UefiDriverVersion": "0x071A0000",
                                "PatrolRead": "Automatic",
                                "PatrolRead@Redfish.AllowableValues": None,
                                "PatrolReadRate": 20,
                                "CompletedPatrolReadIterations": 0,
                                "AlarmPresent": True,
                                "SmartSupport": True,
                                "SmartPollRAID": None,
                                "SmartPollJBOD": None,
                                "CopybackSupport": True,
                                "CopybackSupport@Redfish.AllowableValues": None,
                                "NCQSupport": True,
                                "AutoRebuildSupport": True,
                                "CoercionMode": "None",
                                "CorrectableErrorCount": 0,
                                "UncorrectableErrorCount": 0,
                                "DriveCount": 1,
                                "EncryptedDriveCount": 0,
                                "VolumeCount": 1,
                                "BackupUnit": None,
                                "Capabilities": [
                                    "Encryption"
                                ],
                                "ComponentStatus": None,
                                "AttachMode": "Controller",
                                "BGIRate": 30,
                                "MDCRate": 30,
                                "RebuildRate": 30,
                                "RebuildOperatingMode": None,
                                "RebuildOperatingMode@Redfish.AllowableValues": None,
                                "CopybackOnSMARTErrSupport": True,
                                "CopybackOnSSDSMARTErrSupport": True,
                                "PreservedCache": False,
                                "MDCAbortOnError": False,
                                "NextPatrolReadDateTime": "2025-11-01T03:00:00+00:00",
                                "MigrationRate": 30,
                                "OCERate": None,
                                "MDCScheduleMode": "Disable",
                                "MDCScheduleMode@Redfish.AllowableValues": None,
                                "PatrolReadDelayHour": 168,
                                "PatrolReadMaxDrives": 240,
                                "PatrolReadRecoverySupport": True,
                                "PatrolReadSSDEnabled": False,
                                "SpindownUnconfiguredDrive": True,
                                "SpindownHotspare": True,
                                "SpindownDelayMin": 30,
                                "BIOSStatus": True,
                                "BIOSContinueOnError": "PauseOnErrors",
                                "BIOSContinueOnError@Redfish.AllowableValues": None,
                                "SMARTPollingIntervalSec": 300,
                                "SMARTPollingIntervalSec@Redfish.AllowableValues": None,
                                "DevicesPerSpins": 2,
                                "DevicesPerSpins@Redfish.AllowableValues": None,
                                "SpinupDelaySec": 2,
                                "SpinupDelaySec@Redfish.AllowableValues": None,
                                "AutoFlushIntervalSec": 4,
                                "BootVolumeNumber": 239,
                                "FirstDevice": None,
                                "FirstDevice@Redfish.AllowableValues": None,
                                "ForeignConfig": False,
                                "ContinuousPatrolling": False,
                                "Schedules": [
                                ],
                                "RAIDCapabilities": {
                                    "@odata.id": "/redfish/v1/Systems/0/Storage/0/Oem/ts_fujitsu/RAIDCapabilities"
                                },
                                "RebuildPriority": None,
                                "ExpandPriority": None,
                                "SurfaceAnalysisPriority": None,
                                "ParallelSurfaceScanCurrentCount": None,
                                "DriveWriteCache": {
                                    "Configured": None,
                                    "Unconfigured": None,
                                    "HBA": None
                                },
                                "Connectors": [
                                ],
                                "Family": None,
                                "InternalConnectorCount": None,
                                "ExternalConnectorCount": None,
                                "UpgradeKeyVersion": None,
                                "SupportedBackupRestore": True
                            }
                        },
                        "@odata.id": "/redfish/v1/Systems/0/Storage/0#/StorageControllers/0",
                        "MemberId": "0",
                        "Status": {
                            "State": "Enabled",
                            "Health": "OK",
                            "HealthRollup": "OK",
                            "Oem": {
                            }
                        },
                        "SpeedGbps": 12,
                        "ControllerRates": {
                            "ConsistencyCheckRatePercent": 30,
                            "RebuildRatePercent": 30,
                            "TransformationRatePercent": 30
                        },
                        "FirmwareVersion": "5.260.02-3921",
                        "Location": {
                            "Info": "[ 0 : PCI Slot : 3 ]",
                            "InfoFormat": "[ System_Id : Position : Slot_Id ]"
                        },
                        "Manufacturer": "Fujitsu Limited",
                        "Model": "PRAID EP640i",
                        "Ports": {
                            "@odata.id": "/redfish/v1/Systems/0/Storage/0/Ports"
                        },
                        "SerialNumber": "SKC4912064",
                        "SupportedControllerProtocols": [
                            "PCIe"
                        ],
                        "SupportedDeviceProtocols": [
                            "SAS",
                            "NVMe"
                        ],
                        "SupportedRAIDTypes": [
                            "RAID0",
                            "RAID1",
                            "RAID5",
                            "RAID6",
                            "RAID10",
                            "RAID50",
                            "RAID60",
                            "RAID1E"
                        ],
                        "Identifiers": [
                            {
                                "DurableNameFormat": "NAA",
                                "DurableName": "0x500062B212A6AE80"
                            }
                        ],
                        "Links": {
                            "Oem": {
                            }
                        },
                        "Actions": {
                            "Oem": {
                            }
                        },
                        "Name": "PRAID EP640i (1)"
                    }
                ],
                "Drives": [
                    {
                        "@odata.id": "/redfish/v1/Systems/0/Storage/0/Drives/65536"
                    }
                ],
                "Drives@odata.count": 1,
                "Volumes": {
                    "@odata.id": "/redfish/v1/Systems/0/Storage/0/Volumes"
                },
                "Redundancy@odata.count": 0,
                "Redundancy": [
                ]
            },
            {
                "@odata.id": "/redfish/v1/Systems/0/Storage/1",
                "@odata.type": "#Storage.v1_7_2.Storage",
                "Oem": {
                },
                "Id": "1",
                "Name": "Windows Advanced Host Controller Interface (0)",
                "Links": {
                    "Oem": {
                    },
                    "Enclosures": [
                    ],
                    "Enclosures@odata.count": 0
                },
                "Actions": {
                    "Oem": {
                        "#FTSStorage.CreateVolumes": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.CreateVolumes",
                            "title": "Create volumes for this controller"
                        },
                        "#FTSStorage.DeleteVolumes": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.DeleteVolumes",
                            "title": "Delete volumes from this controller"
                        },
                        "#FTSStorage.DeleteAllVolumes": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.DeleteAllVolumes",
                            "title": "Delete all volumes from this controller",
                            "Command@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/1/Oem/ts_fujitsu/FTSStorageDeleteAllVolumesActionInfo"
                        },
                        "#FTSStorage.Reload": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.Reload",
                            "title": "Relaod storage data from this controller"
                        },
                        "#FTSStorage.PatrolRead": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.PatrolRead",
                            "title": "Control Patrol Read operation for this controller",
                            "Command@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/1/Oem/ts_fujitsu/FTSStoragePatrolReadActionInfo"
                        },
                        "#FTSStorage.ForeignConfiguration": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.ForeignConfiguration",
                            "title": "Manage foreign configuration on this controller",
                            "Command@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/1/Oem/ts_fujitsu/FTSStorageForeignConfigurationActionInfo"
                        },
                        "#FTSStorage.ClearConfiguration": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.ClearConfiguration",
                            "title": "Clear configuration of this controller",
                            "Command@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/1/Oem/ts_fujitsu/FTSStorageClearConfigurationActionInfo"
                        },
                        "#FTSStorage.ClearPreservedCache": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.ClearPreservedCache",
                            "title": "Clear Preserved Cache data of this controller"
                        },
                        "#FTSStorage.ManageSchedule": {
                            "target": "/redfish/v1/Systems/0/Storage/1/Actions/Oem/FTSStorage.ManageSchedule",
                            "title": "Manage Schedule",
                            "Name@Redfish.AllowableValues": [
                            ],
                            "@Redfish.ActionInfo": "/redfish/v1/Systems/0/Storage/1/Oem/ts_fujitsu/FTSStorageManageScheduleActionInfo"
                        }
                    }
                },
                "Status": {
                    "State": "Enabled",
                    "Health": "OK",
                    "HealthRollup": "OK",
                    "Oem": {
                    }
                },
                "StorageControllers@odata.count": 1,
                "StorageControllers": [
                    {
                        "Oem": {
                            "ts_fujitsu": {
                                "@odata.type": "#FTSStorageController.v3_6_0.FTSStorageController",
                                "ControllerNumber": None,
                                "VendorId": None,
                                "DeviceId": None,
                                "SubsystemVendorId": None,
                                "SubsystemId": None,
                                "FirmwarePackageVersion": None,
                                "FirmwareBuildDate": None,
                                "BiosVersion": None,
                                "BiosBuildDate": None,
                                "MemorySizeMiB": None,
                                "FlashRomSizeMiB": None,
                                "NvramSizeKiB": None,
                                "ChipTemperatureC": None,
                                "PortCount": None,
                                "PCISegmentNumber": None,
                                "PCIBusNumber": None,
                                "PCIDeviceNumber": None,
                                "PCIFunctionNumber": None,
                                "DriverName": "storahci",
                                "DriverVersion": "10.0.26100.1150",
                                "UefiDriverVersion": None,
                                "PatrolRead": None,
                                "PatrolRead@Redfish.AllowableValues": None,
                                "PatrolReadRate": None,
                                "CompletedPatrolReadIterations": None,
                                "AlarmPresent": False,
                                "SmartSupport": False,
                                "SmartPollRAID": None,
                                "SmartPollJBOD": None,
                                "CopybackSupport": None,
                                "CopybackSupport@Redfish.AllowableValues": None,
                                "NCQSupport": None,
                                "AutoRebuildSupport": None,
                                "CoercionMode": None,
                                "CorrectableErrorCount": 0,
                                "UncorrectableErrorCount": 0,
                                "DriveCount": 0,
                                "EncryptedDriveCount": 0,
                                "VolumeCount": 0,
                                "BackupUnit": None,
                                "Capabilities": [
                                ],
                                "ComponentStatus": None,
                                "AttachMode": "Controller",
                                "BGIRate": None,
                                "MDCRate": None,
                                "RebuildRate": None,
                                "RebuildOperatingMode": None,
                                "RebuildOperatingMode@Redfish.AllowableValues": None,
                                "CopybackOnSMARTErrSupport": None,
                                "CopybackOnSSDSMARTErrSupport": None,
                                "PreservedCache": None,
                                "MDCAbortOnError": None,
                                "NextPatrolReadDateTime": None,
                                "MigrationRate": None,
                                "OCERate": None,
                                "MDCScheduleMode": None,
                                "MDCScheduleMode@Redfish.AllowableValues": None,
                                "PatrolReadDelayHour": None,
                                "PatrolReadMaxDrives": None,
                                "PatrolReadRecoverySupport": None,
                                "PatrolReadSSDEnabled": None,
                                "SpindownUnconfiguredDrive": None,
                                "SpindownHotspare": None,
                                "SpindownDelayMin": None,
                                "BIOSStatus": None,
                                "BIOSContinueOnError": None,
                                "BIOSContinueOnError@Redfish.AllowableValues": None,
                                "SMARTPollingIntervalSec": None,
                                "SMARTPollingIntervalSec@Redfish.AllowableValues": None,
                                "DevicesPerSpins": None,
                                "DevicesPerSpins@Redfish.AllowableValues": None,
                                "SpinupDelaySec": None,
                                "SpinupDelaySec@Redfish.AllowableValues": None,
                                "AutoFlushIntervalSec": None,
                                "BootVolumeNumber": None,
                                "FirstDevice": None,
                                "FirstDevice@Redfish.AllowableValues": None,
                                "ForeignConfig": None,
                                "ContinuousPatrolling": None,
                                "Schedules": [
                                ],
                                "RAIDCapabilities": None,
                                "RebuildPriority": None,
                                "ExpandPriority": None,
                                "SurfaceAnalysisPriority": None,
                                "ParallelSurfaceScanCurrentCount": None,
                                "DriveWriteCache": {
                                    "Configured": None,
                                    "Unconfigured": None,
                                    "HBA": None
                                },
                                "Connectors": [
                                ],
                                "Family": None,
                                "InternalConnectorCount": None,
                                "ExternalConnectorCount": None,
                                "UpgradeKeyVersion": None,
                                "SupportedBackupRestore": None
                            }
                        },
                        "@odata.id": "/redfish/v1/Systems/0/Storage/1#/StorageControllers/0",
                        "MemberId": "0",
                        "Status": {
                            "State": "Enabled",
                            "Health": "OK",
                            "HealthRollup": "OK",
                            "Oem": {
                            }
                        },
                        "SpeedGbps": None,
                        "ControllerRates": {
                            "ConsistencyCheckRatePercent": None,
                            "RebuildRatePercent": None,
                            "TransformationRatePercent": None
                        },
                        "FirmwareVersion": None,
                        "Location": {
                        },
                        "Manufacturer": None,
                        "Model": "Advanced Host Controller Interface",
                        "Ports": {
                            "@odata.id": "/redfish/v1/Systems/0/Storage/1/Ports"
                        },
                        "SerialNumber": None,
                        "SupportedControllerProtocols": [
                            "AHCI"
                        ],
                        "SupportedDeviceProtocols": [
                        ],
                        "SupportedRAIDTypes": [
                        ],
                        "Identifiers": [
                        ],
                        "Links": {
                            "Oem": {
                            }
                        },
                        "Actions": {
                            "Oem": {
                            }
                        },
                        "Name": "Windows Advanced Host Controller Interface (0)"
                    }
                ],
                "Drives": [
                ],
                "Drives@odata.count": 0,
                "Volumes": {
                    "@odata.id": "/redfish/v1/Systems/0/Storage/1/Volumes"
                },
                "Redundancy@odata.count": 0,
                "Redundancy": [
                ]
            }
        ],
        "Members@odata.count": 2,
        "Oem": {
        },
        "@Redfish.Copyright": "Copyright 2014-2020 DMTF. For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright"
    }
