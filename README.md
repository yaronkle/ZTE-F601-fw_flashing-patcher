# ZTE-F601-fw_flashing-patcher

The ZTE F601 GPON ONU FTTH version 6.0.10P1T12 does not allow downgrading to a 6.0.1P1T12.
The fw_flashing binary on the device checks the version.

The following repository has a patched6.0.10P1T12 binary that allows downgrading.
The python script backs up the fw_flashing on the device and pushes the patched version instead.

After the script succeeds it is possible to flash any 6.0.1 version on the device.

## usage instructions

zte_fw_flashing.py [optional --file] [optional --zte_ip] [optional --ftp_only]

--file < patched fw_flashing file > if no file given then script will try to find fw_flashing.patched_6.0.10T12 in the current folder

--zte_ip < ip of ZTE box > If no ip is given then script will use 192.168.1.1 as the ip of the ZTE

--ftp_only Just push the file using FTP. Don't try to re-enable FTP service
