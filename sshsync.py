import os
import pathlib
import datetime
import time
import re
import logging
import argparse
import yaml
import paramiko

class Utility:
    def run(self):
        self.ssh = None
        self.parse_parameters()
        options = self.options
        self.current_timestamp = datetime.datetime.fromtimestamp(time.time())
        print(self.current_timestamp)
        self.load_data_store()
        if options.reset:
            self.update_data_store()
            return
        self.process_files()
        if not self.files_found:
            print('nothing to synchronize')
            return
        if options.preview:
            return
        self.update_data_store()
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()

    def parse_parameters(self):
        parser = argparse.ArgumentParser(description='SSH synchronization utility')
        parser.add_argument('-p', '--preview', action='store_true', help='preview mode')
        parser.add_argument('-r', '--reset', action='store_true', help='only reset starting point')
        parser.add_argument('-a', '--all', action='store_true', help='synchronize all')
        parser.add_argument('data_store', help='YAML data store')
        parser.add_argument('root', help='root directory to synchronize')
        self.options = parser.parse_args()

    def load_data_store(self):
        self.data_store = yaml.load(open(self.options.data_store).read(), Loader=yaml.Loader)
        data_store = self.data_store
        self.start_timestamp = None
        if 'timestamp' not in data_store:
            return
        self.start_timestamp = datetime.datetime.strptime(data_store['timestamp'], '%Y-%m-%d %H:%M:%S.%f')

    def update_data_store(self):
        data_store = self.data_store
        data_store['timestamp'] = str(self.current_timestamp)
        open(self.options.data_store, 'w').write(yaml.dump(data_store, sort_keys=False))
        print('starting point set')

    def process_files(self):
        file_names = []
        for root, folders, files in os.walk(self.options.root):
            file_names.extend([os.path.join(root, file) for file in files])
        self.files_found = False
        for file_name in file_names:
            self.process_file(file_name)

    def process_file(self, file_name):
        options = self.options
        data_store = self.data_store
        if file_name == options.data_store:
            return
        file_name = file_name.replace('\\', '/')
        if not re.match(data_store['filter'], file_name):
            return
        if self.start_timestamp and not options.all:
            changed = os.path.getmtime(file_name)
            changed = datetime.datetime.fromtimestamp(changed)
            if changed < self.start_timestamp:
                return
        self.files_found = True
        mapping = data_store['mapping'].replace('$', '\\')
        remote_file_name = file_name[len(self.options.root) + 1:]
        remote_file_name = re.sub(data_store['filter'], mapping, remote_file_name)
        if options.preview:
            print(f'{file_name} -> {remote_file_name}')
        else:
            self.upload_file(file_name, remote_file_name)

    def upload_file(self, local_path, remote_path):
        if not self.ssh:
            ssh = paramiko.SSHClient()
            self.ssh = ssh
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            data_store = self.data_store
            hostname = re.match(r'ssh://(.*)', data_store['url']).group(1)
            print(f'connecting to {hostname}')
            ssh.connect(hostname, username=data_store['username'], password=data_store['password'])
            self.sftp = ssh.open_sftp()
        sftp = self.sftp
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.chdir(remote_dir)
        except IOError:
            print(f'creating {remote_dir} directory')
            sftp.mkdir(remote_dir)
        remote_file = sftp.open(remote_path, 'w')
        print(f'{local_path} -> {remote_path}')
        remote_file.write(open(local_path).read())
        stdin, stdout, stderr = self.ssh.exec_command(f"chtag -tc ISO8859-1 '{remote_path}'")

if __name__ == '__main__':
    Utility().run()
