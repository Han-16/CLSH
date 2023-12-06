#!/usr/bin/env python3
import subprocess
import argparse
import os
import threading
from queue import Queue

print_semaphore = threading.Semaphore()
output_queue = Queue()

def get_node_names():
    # CLSH_HOSTS 환경 변수에서 호스트 이름 읽어오기
    clsh_hosts = os.environ.get('CLSH_HOSTS')
    if clsh_hosts:
        return clsh_hosts.split(':')

    # CLSH_HOSTFILE 환경 변수에서 파일 이름 읽어오기
    clsh_hostfile = os.environ.get('CLSH_HOSTFILE')
    if clsh_hostfile:
        try:
            with open(clsh_hostfile, 'r') as f:
                return f.read().splitlines()
        except FileNotFoundError:
            pass  # 파일이 없는 경우 계속 진행

    # 현재 디렉토리에서 .hostfile에서 읽어오기
    default_hostfile = '.hostfile'
    try:
        with open(default_hostfile, 'r') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        pass  # 파일이 없는 경우 계속 진행

    # 모든 시도가 실패한 경우
    raise ValueError("--hostfile 옵션이 제공되지 않았습니다.")

def worker(node, command):
    # ssh를 통해 컨테이너와 통신
    ssh_command = ["ssh", "-T", node] + command
    proc = subprocess.Popen(ssh_command,
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    with print_semaphore:
        output = (node, stdout, stderr, proc.returncode)
        output_queue.put(output)


def print_output():
    while True:
        output = output_queue.get()
        if output is None:
            break

        with print_semaphore:
            # 결과를 로컬 터미널에 출력
            node, stdout, stderr, returncode = output
            output_str = f'{node}: {stdout.decode().strip()}\n' if returncode == 0 else f'{node}: ERROR: {stderr.decode().strip()}\n'
            print(output_str, end='', flush=True)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostfile', type=str, default=None)
    parser.add_argument('command', type=str, nargs='+')
    args = parser.parse_args()

    if args.hostfile is None:
         # --hostfile 옵션이 제공되지 않은 경우, 환경 변수 및 기본 파일에서 호스트 정보 읽어오기
        try:
            nodes = get_node_names()
        except ValueError as e:
            print(f"Error: {str(e)}")
            return
    else:
         # --hostfile 옵션이 제공된 경우 해당 파일에서 호스트 정보 읽어오기
        with open(args.hostfile, 'r') as f:
            nodes = f.read().splitlines()


    threads = []
    for node in nodes:
        # 각 노드에 대해 별도의 쓰레드를 생성하여 worker 함수를 실행
        t = threading.Thread(target=worker, args=(node, args.command))
        threads.append(t)
        t.start()

    print_thread = threading.Thread(target=print_output)
    print_thread.start()

    # 모든 쓰레드가 종료될 때까지 기다림
    for t in threads:
        t.join()
    output_queue.put(None)
    print_thread.join()

if __name__ == "__main__":
    main()
