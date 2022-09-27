# ZTE-F601-fw_flashing-patcher

The ZTE F601 GPON ONU FTTH version 6.0.10P1T12 does not allow downgrading to a 6.0.1P1T12.
The fw_flashing binary on the device checks the version.

The following repository has a patched6.0.10P1T12 binary that allows downgrading.
The python script backs up the fw_flashing on the device and pushes the patched version instead.

After the script succeeds it is possible to flash any 6.0.1 version on the device.
