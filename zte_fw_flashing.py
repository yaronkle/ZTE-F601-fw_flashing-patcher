import sys
import argparse
from time import sleep
from telnetlib import Telnet
from ftplib import FTP

__version__ = "1.0.0"

TELNET_USER = 'root'
TELNET_PASSWORD = 'Zte521'
FTP_USER = 'admin'
FTP_PASSWORD = 'admin'
TIMEOUT = 4
REBOOT_TIMEOUT = 60*3


class Zte(object):
    def __init__(self, host, patched_fw_flashing, ftp_only, ignore_version_check):
        self.host = host
        self.patched_fw_flashing = patched_fw_flashing
        self.ftp_only = ftp_only
        self.ignore_version_check = ignore_version_check
        self.telnet = Telnet()

    def login(self, timeout):

        print("Connecting via telnet")
        try:
            telnet_port = 23
            self.telnet.open(self.host, telnet_port, TIMEOUT)
        except Exception as e:
            print('Cound not connect {0}'.format(e))
            return False

        result = self.telnet.read_until(b"Login: ", TIMEOUT)

        if len(result) > 0:
            self.telnet.write(TELNET_USER.encode('ascii') +b"\n")
            self.telnet.read_until(b"Password: ", TIMEOUT)
            self.telnet.write(TELNET_PASSWORD.encode('ascii') +b"\n")
            result = self.telnet.read_until(b"# ", TIMEOUT)

        login_success = len(result) >= 2 and result[-2:] == b"# "
        if login_success:
            print('telnet successfully logged in')
        else:
            print('Could not telnet device')

        return login_success


    def verify_device_version(self):
        return True

    def telnet_write_and_wait_for_prompt(self, data):
        self.telnet.write(data + b" \n")
        return self.telnet.read_until(b"# ", TIMEOUT)

    def enable_ftp(self):
        print('Enabling FTP server')
        self.telnet_write_and_wait_for_prompt(b"sendcmd 1 DB set FTPServerCfg 0 FtpEnable 1")
        self.telnet_write_and_wait_for_prompt(b"sendcmd 1 DB set FTPServerCfg 0 WanIfEnable 1")
        self.telnet_write_and_wait_for_prompt(b"sendcmd 1 DB save")

    def reboot(self):
        sleep(5)
        print('Rebooting')
        self.telnet.write(b"reboot \n")
        sleep(60)

    def backup_fw_flashing(self):
        result = self.telnet_write_and_wait_for_prompt(b"ls /bin/fw_flashing.orig")
        print('ls result {0}'.format(result))

        if 'No such file'.encode('utf-8') in result:
            print('Backing up /bin/fw_flashing to /bin/fw_flashing.orig')
            self.telnet_write_and_wait_for_prompt(b"cp /bin/fw_flashing /bin/fw_flashing.orig")
        else:
            print('fw_flashing already backed up as /bin/fw_flashing.orig')

    def transfer_patched_file(self):

        print('setting up file for ftp')
        self.telnet_write_and_wait_for_prompt(b"echo aa > /mnt/" + self.patched_fw_flashing.encode('ascii'))
        self.telnet_write_and_wait_for_prompt(b"chmod 777 /mnt/" + self.patched_fw_flashing.encode('ascii'))

        print('FTP device')
        ftp = FTP()
        ftp.connect(self.host)
        ftp.login(FTP_USER, FTP_PASSWORD)

        ftp_response = ""
        print('Pushing patched binary to device')
        with open(self.patched_fw_flashing, "rb") as ftp_local_file:
            ftp_response = ftp.storbinary("STOR " + self.patched_fw_flashing, ftp_local_file)

        print('FTP response:{0}'.format(ftp_response))

        if "226" in ftp_response:
            print('copying back to /bin/fw_flashing')
            self.telnet_write_and_wait_for_prompt(b"cp /mnt/" + self.patched_fw_flashing.encode('ascii') + b"/bin/fw_flashing")

    def execute(self):
        if not self.ftp_only:
            if self.login(TIMEOUT):
                if self.verify_device_version():
                    self.enable_ftp()
                    self.reboot()
                    self.telnet.close()
                    print('Logging in after reboot')

        if self.login(TIMEOUT):
            self.backup_fw_flashing()
            self.transfer_patched_file()

            print('Patching finished.')
            print('You can now flash firmware')

        self.telnet.close()

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, required=False, help='Patched fw_flashing file for the specific version running on the ZTE')
    parser.add_argument('--host', type=str, required=False, help='Host IP address. Default is 192.168.1.1')
    parser.add_argument('--ftp_only', default=False, action='store_true', help='True = Skip enabling the FTP server and reboot.')
    parser.add_argument('--ignore_version_check', default=False, action='store_true', help='TODO: True = Skip checking bootloader version')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    patched_fw_flashing = "fw_flashing.patched_6.0.10T12"
    if args.file:
        patched_fw_flashing = args.file

    host = "192.168.1.1"
    if args.host:
        host = args.host

    zte = Zte(host, patched_fw_flashing, args.ftp_only, args.ignore_version_check)

    try:
        zte.execute()
        input("Press Enter to continue...")

    except Exception as e:
        print('zte_fw_flashing failed {0}'.format(e))




