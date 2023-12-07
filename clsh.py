import sys
import os
import argparse
import concurrent.futures
import subprocess
from queue import Queue

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


def worker(node, command, out_dir=None, err_dir=None):
    # command[0]에 xargs가 들어있다면, xargs를 사용하여 명령을 실행
    if command and command[0] == 'xargs':
        # command[1:]에 있는 명령을 xargs로 실행
        xargs_command = ' '.join(command[1:])
        ssh_command = f"ssh -T {node} sudo {xargs_command}"
    else:
        # 일반적인 경우, 주어진 명령을 그대로 실행
        ssh_command = f"ssh -T {node} {' '.join(command)}"
    # print(f"ssh_command : {ssh_command}")
    try:
        # Popen을 사용하여 ssh 명령을 실행하고 파이프를 통해 통신
        process = subprocess.Popen(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True,
            text=True
        )

        stdout, stderr = process.communicate(input="")
        returncode = process.returncode
        result_message = None

        if out_dir or err_dir:
            if out_dir is None:  # only --err
                if returncode == 0:  # success
                    result_message = f"Command executed successfully."
                else:  # failed
                    os.makedirs(err_dir, exist_ok=True)
                    err_path = os.path.join(err_dir, f"{node}.err")

                    with open(err_path, 'w') as err_file:
                        err_file.write(stderr)

                    result_message = f"ERROR!! Stderr saved to: {err_path}"

            elif err_dir is None:  # only --out
                if returncode == 0:  # success
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, f"{node}.out")

                    with open(out_path, 'w') as out_file:
                        out_file.write(stdout)
                    result_message = f"Success!! Result saved to: {out_path}"

                else:  # failed
                    result_message = f"Error executing command."

            else:  # --out --err
                if returncode == 0:  # success
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, f"{node}.out")

                    with open(out_path, 'w') as out_file:
                        out_file.write(stdout)

                    result_message = f"Success!! Result saved to: {out_path}"
                else:  # failed
                    os.makedirs(err_dir, exist_ok=True)
                    err_path = os.path.join(err_dir, f"{node}.err")

                    with open(err_path, 'w') as err_file:
                        err_file.write(stderr)

                    result_message = f"ERROR!! Stderr saved to: {err_path}"
            return node, stdout, stderr, returncode, result_message

        else:
            return node, stdout, stderr, returncode, result_message

    except Exception as e:
        return node, f"There is something wrong with {node}: {str(e)}"


def print_output():
    while True:
        output = output_queue.get()
        if output is None:
            break
        node, stdout, stderr, returncode, result_message = output
        if result_message:
            output_str = f'{node}: {result_message}\n' if returncode == 0 else f'{node}: {result_message}\n'
            print(output_str, end='', flush=True)
        else:
            output_str = f'{node}: {stdout}' if returncode == 0 else f'{node}: {stderr}'
            print(output_str, end="")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostlist', type=str, default=None)
    parser.add_argument('--hostfile', type=str, default=None)
    parser.add_argument('--out', type=str, default=None)
    parser.add_argument('--err', type=str, default=None)
    parser.add_argument('command', type=str, nargs='+')
    args = parser.parse_args()

    # 명령행 인수 파싱 시 파이프로 전달된 데이터를 추가로 받음
    if not sys.stdin.isatty():
        # sys.stdin이 터미널이 아닌 경우 파이프로 데이터를 받아옴
        stdin_data = sys.stdin.read().strip()
        # 받아온 데이터를 명령행 인수로 추가
        args.command = ['xargs', *args.command, stdin_data]

    if args.hostlist:
        nodes = args.hostlist.split(',')
    elif args.hostfile is None:
        try:
            nodes = get_node_names()
        except ValueError as e:
            return
    else:
        with open(args.hostfile, 'r') as f:
            nodes = f.read().splitlines()

    out_dir = args.out if args.out else None
    err_dir = args.err if args.err else None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 각 노드에 대한 worker 함수를 스레드 풀에서 실행
        futures = [executor.submit(
            worker, node, args.command, out_dir, err_dir) for node in nodes]

        # Future의 결과를 가져와 출력 큐에 넣음
        for future in concurrent.futures.as_completed(futures):
            output_queue.put(future.result())

    # 모든 worker 스레드 종료 후에 None 큐에 넣음
    output_queue.put(None)

    # 스레드의 결과를 출력
    print_output()


if __name__ == "__main__":
    main()
