import sys
import argparse
import os.path
from time import sleep
from telnetlib import Telnet
from ftplib import FTP

__version__ = "1.0.8"

ZTE_IP = "192.168.1.1"
TELNET_USER = 'root'
TELNET_PASSWORD = 'Zte521'
FTP_USER = 'admin'
FTP_PASSWORD = 'admin'
PATCHED_FW_FLASHING = "fw_flashing.patched_6.0.10T12"
TIMEOUT = 4
REBOOT_TIMEOUT = 60*3

class Zte(object):
    def __init__(self, zte_ip, patched_fw_flashing, ftp_only, telnet_user, telnet_password, ftp_user, ftp_password):
        self.zte_ip = zte_ip
        self.patched_fw_flashing = patched_fw_flashing
        self.ftp_only = ftp_only
        self.telnet_user = telnet_user
        self.telnet_password = telnet_password
        self.ftp_user = ftp_user
        self.ftp_password = ftp_password
        self.telnet = Telnet()

    def login(self, timeout):

        print("Connecting via telnet")
        try:
            telnet_port = 23
            self.telnet.open(self.zte_ip, telnet_port, TIMEOUT)
        except Exception as e:
            print('Error could not connect {0}'.format(e))
            return False

        result = self.telnet.read_until(b"Login: ", TIMEOUT)

        if len(result) > 0:
            self.telnet.write(self.telnet_user.encode('ascii') +b"\n")
            self.telnet.read_until(b"Password: ", TIMEOUT)
            self.telnet.write(self.telnet_password.encode('ascii') +b"\n")
            result = self.telnet.read_until(b"# ", TIMEOUT)

        login_success = len(result) >= 2 and result[-2:] == b"# "
        if login_success:
            print('telnet successfully logged in')
        else:
            print('Error could not telnet device')

        return login_success

    def telnet_write_and_wait_for_prompt(self, data):
        self.telnet.write(data + b" \n")
        return self.telnet.read_until(b"# ", TIMEOUT)

    def enable_ftp(self):
        print('Enabling FTP server')
        self.telnet_write_and_wait_for_prompt(b"sendcmd 1 DB set FTPServerCfg 0 FtpEnable 1")
        self.telnet_write_and_wait_for_prompt(b"sendcmd 1 DB set FTPServerCfg 0 WanIfEnable 1")
        self.telnet_write_and_wait_for_prompt(b"sendcmd 1 DB save")

    def reboot(self):
        print('Rebooting')
        sleep(5)
        self.telnet.write(b"reboot \n")
        sleep(60) # TODO: wait for device to restart instead of sleep

    def backup_fw_flashing(self):
        result = self.telnet_write_and_wait_for_prompt(b"ls /bin/fw_flashing.orig")

        if 'No such file'.encode('utf-8') in result:
            print('Backing up /bin/fw_flashing to /bin/fw_flashing.orig')
            self.telnet_write_and_wait_for_prompt(b"cp /bin/fw_flashing /bin/fw_flashing.orig")
        else:
            print('fw_flashing already backed up as /bin/fw_flashing.orig')

    def create_all_permissions_file_in_mnt(self):
        print('Setting up file for ftp')
        # User admin admin does not have write access to folder /mnt/
        # In order to overcome this, create a dummy file in /mnt with all permissions 777
        # ftp client will be overwrite that file
        self.telnet_write_and_wait_for_prompt(b"echo aa > /mnt/" + self.patched_fw_flashing.encode('ascii'))
        self.telnet_write_and_wait_for_prompt(b"chmod 777 /mnt/" + self.patched_fw_flashing.encode('ascii'))

    def transfer_patched_file(self):
        self.create_all_permissions_file_in_mnt()

        print('FTP device')
        ftp = FTP()
        ftp.connect(self.zte_ip)
        ftp.login(self.ftp_user, self.ftp_password)

        ftp_response = ""
        print('Pushing patched binary to device')
        with open(self.patched_fw_flashing, "rb") as ftp_local_file:
            ftp_response = ftp.storbinary("STOR " + self.patched_fw_flashing, ftp_local_file)

        print('FTP response:{0}'.format(ftp_response))

        if "226" in ftp_response:
            self.telnet_write_and_wait_for_prompt(b"cp /mnt/" + self.patched_fw_flashing.encode('ascii') + b" /bin/fw_flashing")

    def execute(self):
        if not os.path.exists(self.patched_fw_flashing):
            print('Error file {0} does not exit\n'.format(self.patched_fw_flashing))
        else:
            if not self.ftp_only:
                if self.login(TIMEOUT):
                    self.enable_ftp()
                    # reboot is required for FTP to be enabled
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
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--file', type=str, required=False, help='Patched fw_flashing file for the specific version running on the ZTE')
    parser.add_argument('--zte_ip', type=str, default=str(ZTE_IP), required=False, help='IP of ZTE device.')
    parser.add_argument('--ftp_only', default=False, action='store_true', help='True = Skip enabling the FTP server and reboot.')
    parser.add_argument('--telnet_user', type=str, default=str(TELNET_USER), required=False, help='Telnet username')
    parser.add_argument('--telnet_password', type=str, default=str(TELNET_PASSWORD), required=False, help='Telnet password')
    parser.add_argument('--ftp_user', type=str, default=str(FTP_USER), required=False, help='FTP username')
    parser.add_argument('--ftp_password', type=str, default=str(FTP_PASSWORD), required=False, help='FTP password')
    parser.add_argument('--patched_fw_flashing', type=str, default=str(PATCHED_FW_FLASHING), required=False, help='Name of the patched fw_flashing file that allows downgrade')
    return parser.parse_args()


if __name__ == '__main__':
    print('zte_fw_flashing {0}\n'.format(__version__))

    args = parse_arguments()

    zte = Zte(args.zte_ip, args.patched_fw_flashing, args.ftp_only, args.telnet_user, args.telnet_password, args.ftp_user, args.ftp_password)

    try:
        zte.execute()
        input("Press Enter to continue...")

    except Exception as e:
        print('Error zte_fw_flashing failed {0}'.format(e))
        input("Press Enter to continue...")




