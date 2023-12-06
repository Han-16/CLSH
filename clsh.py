import subprocess
import argparse
import os
import threading
from queue import Queue
import shlex

print_semaphore = threading.Semaphore()
output_queue = Queue()

def get_node_names():
    clsh_hosts = os.environ.get('CLSH_HOSTS')
    if clsh_hosts:
        return clsh_hosts.split(':')

    clsh_hostfile = os.environ.get('CLSH_HOSTFILE')
    if clsh_hostfile:
        try:
            with open(clsh_hostfile, 'r') as f:
                return f.read().splitlines()
        except FileNotFoundError:
            pass

    default_hostfile = '.hostfile'
    try:
        with open(default_hostfile, 'r') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        pass

    raise ValueError("--hostfile 옵션이 제공되지 않았습니다.")


def worker(node, command):
    ssh_command = ["ssh", "-T", node] + command

    try:
        # 명령어를 올바르게 파싱하기 위해 shlex.split을 사용
        command_for_subprocess = shlex.split(" ".join(ssh_command))

        # Popen을 사용하여 ssh 명령을 실행하고 파이프를 통해 통신
        proc = subprocess.Popen(
            command_for_subprocess,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,  # 추가: 표준 입력에 대한 파이프
            text=True
        )
        stdout, stderr = proc.communicate(input="")
        returncode = proc.returncode
    except subprocess.CalledProcessError as e:
        stdout = ""
        stderr = e.stderr
        returncode = e.returncode

    with print_semaphore:
        output = (node, stdout, stderr, returncode)
        output_queue.put(output)

def print_output():
    while True:
        output = output_queue.get()
        if output is None:
            break

        with print_semaphore:
            node, stdout, stderr, returncode = output
            output_str = f'{node}: {stdout.strip()}\n' if returncode == 0 else f'{node}: ERROR: {stderr.strip()}\n'
            print(output_str, end='', flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostlist', type=str, default=None)
    parser.add_argument('--hostfile', type=str, default=None)
    parser.add_argument('command', type=str, nargs='+')
    args = parser.parse_args()

    if args.hostlist is not None:
        # -hostlist 옵션이 제공된 경우 해당 노드 리스트 사용
        nodes = args.hostlist.split(',')
    elif args.hostfile is None:
        try:
            nodes = get_node_names()
        except ValueError as e:
            print(f"Error: {str(e)}")
            return
    else:
        with open(args.hostfile, 'r') as f:
            nodes = f.read().splitlines()

    threads = []
    for node in nodes:
        t = threading.Thread(target=worker, args=(node, args.command))
        threads.append(t)
        t.start()

    print_thread = threading.Thread(target=print_output)
    print_thread.start()

    for t in threads:
        t.join()
    output_queue.put(None)
    print_thread.join()

if __name__ == "__main__":
    main()
