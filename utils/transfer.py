import getpass
import random
import subprocess
import time

import pexpect
import paramiko
import os


def transfer_files(subject_id, host, user, password, source, destination, session_date=None, **kwargs):
    # initialize ssh client
    ssh_client = paramiko.SSHClient()
    # accept keys
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    ssh_client.connect(hostname=host, username=user, password=password)
    ssh_client.get_transport().window_size = 3*1024*1024


    # making sure remote path exists
    stdout, stdin, stderr =ssh_client.exec_command(f"mkdir -p {destination}")
    print(f"{stdout} \n{stdin}\n{stderr}")
    # creating filepath with subject_id_session_date in folder name
    if not session_date:
        session_date = ''
    else:
        session_date = '_' + str(session_date)
    remotepath_w_subject_folder = os.path.join(destination, str(subject_id) + str(session_date))

    # creating subject folder
    stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remotepath_w_subject_folder}")

    # creating an ftp client with our ssh client
    ftp_client = ssh_client.open_sftp()
    for root, folders, files in os.walk(source):
        for file in files:
            localfile = os.path.join(root, file)
            remotefile = os.path.join(remotepath_w_subject_folder, file)
            ftp_client.put(localfile, remotefile)
    ftp_client.close()


def login_and_sync(subject_id, session_date, source, destination, user, host, password=None):
    # TODO Add some error handling, seriously. Namely incorrect user, failed password, and host does not exist.
    # TODO You need to take into account accepting the key thingy when ssh/scp/rsync first
    # TODO generates when connecting to a new server.
    """
    This function provide a means for the user to transfer their data between the local server to
    either a remote server or locally using scp. This function uses pexpect is similar to calling a linux command with
    subprocess. Pexpect provides some additional benefits however, namely it keeps things such as passwords and entered
    text from appearing in bash history and it's designed to respond to text prompts that it's instructed to recieve.

    In this specific case pexpect calls scp with it's requisite arguments then waits for scp to open up a password
    prompt. Once that prompt appears the password argument above is provided to pexpect and scp does it's magic.
    :param subject_id: subject_id of session
    :param session_date: date of session
    :param source: The source file or folder to be transmitted
    :param destination: The filepath the user wishes to deliver the file to.
    :param user: The user at the destination host, it's this user's password that will be required for this function
    to work.
    :param host: The machine to deliver files/folders to from the where this code is locally.
    :param password: user's password, passed in as string.
    """
    if not source:
        raise Exception("Must provide source data to be transferred")
    if not destination:
        raise Exception("Must provide destination to transmit data to.")
    # if no host is provided it will be assumed that transfer should occur locally
    if not host:
        cmd = 'rsync -rt ' + \
              '{source} {destination}/{subject_id}_{session_date}'.format(source=source,
                                                                          destination=destination,
                                                                          subject_id=subject_id,
                                                                          session_date=session_date)

        child = pexpect.spawn(cmd)
        child.expect(pexpect.EOF)  # if this isn't present transfer will be cut off before it can complete.
        child.close()

    # if host is provide use this alternate command and pass it a password.
    else:
        # first make destination folder on remote host
        # ssh galassi@exahead1 "mkdir -p /home/exacloud/lustre1/fnl_lab/scratch/new_folder"
        make_dir_cmd = 'ssh {user}@{host} "mkdir -p {destination}/{subject_id}_{session_date}"'.format(user=user,
                                                                                                       host=host,
                                                                                                       destination=destination,
                                                                                                       subject_id=subject_id,
                                                                                                       session_date=session_date)
        print(f"making directory at destination \n {make_dir_cmd}")
        make_dir_child = pexpect.spawn(make_dir_cmd)
        connection = make_dir_child.expect(['password:', 'Are you sure you want to continue connecting'], timeout=None)
        if connection == 0:
            make_dir_child.sendline(password)
        elif 1:
            print("got this response", make_dir_child.before, make_dir_child.after)
            make_dir_child.sendline('yes')
            make_dir_child.expect('to the list of known hosts.')
            make_dir_child.sendline(password)
        make_dir_child.expect(pexpect.EOF)
        make_dir_child.close()

        # we only want files! this command works in bash but not yet in pexpect
        '''
        shopt -s globlstar
        rsync -a --delete --include=*.dcm --exclude=* {source_dir}/** {destination_dir}
        '''

        # this may be another option
        """
        rsync -a -f"- */" -f"+ *" {source_dir} {destination_dir}
        """

        # although it turns out it's easier to user rsync if we want to excluded tmp_dcm2bids (which we do)
        cmd = 'shopt -s globstar ' + \
              'rsync -a --delete --include=*.dcm --exclude=* ' + \
              '{source}/** {user}@{host}:{destination}/{subject_id}_{session_date}' \
              ' && echo completed'.format(source=source,
                                          user=user,
                                          host=host,
                                          destination=destination,
                                          subject_id=subject_id,
                                          session_date=session_date)
        cmd = 'rsync -a -f"- */" -f"+ *"' + '{source} {user}@{host}:{destination}/{subject_id}_{session_date}'.format(
            source=source,
            user=user,
            host=host,
            destination=destination,
            subject_id=subject_id,
            session_date=session_date)
        print(cmd)
        args = ["-c", cmd]
        child = pexpect.spawn('/bin/bash', args=args)
        print("sent {} using /bin/bash -c ".format(cmd))
        time.sleep(random.random() * random.randrange(1, 5) + .33)  # I don't think this is necessary, but it don't hurt
        child.expect('password:', timeout=None)
        child.sendline(password)
        print("sent and received password")
        # child.wait()
        # child.expect(pexpect.EOF, timeout=None)  # if this isn't present transfer will be cut off before it can complete
        if child.isalive():
            print("child is still alive")

        child.sendline("echo $?")
        if child.isalive():
            print("STill alive but about to be killed with close")
        # child.close()

        while child.isalive():
            time.sleep(1)
            print("Child is still alive")

        # after closing the moving subprocess we want to collect the status of the move
        signal_status = child.signalstatus
        exit_code = child.exitstatus
        print("Exit code {}".format(exit_code))


if __name__ == "__main__":
    # prompt user for password:
    print("Enter your login credentials below:")
    source = input("Enter source: ")
    destination = input("Enter Destination: ")
    user = input("Enter Username: ")
    host = input("Enter Hostname: ")
    password1 = ''
    password2 = '1'
    while password1 != password2:
        password1 = getpass.getpass()
        password2 = getpass.getpass(prompt="Confirm Password:")
        if password1 != password2:
            print("Passwords do not match. Try again")
    for i in range(1):
        destination = destination
        login_and_sync(source=source, destination=destination, user=user, host=host, password=password1)
