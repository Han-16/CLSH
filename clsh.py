import sys
import os
import argparse
import concurrent.futures
import subprocess
from queue import Queue
import threading
import shlex

output_queue = Queue()
input_lock = threading.Lock()  # Lock for synchronizing input


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
        xargs_command = ' '.join(command[1:])
        ssh_command = f"ssh -T {node} {xargs_command}"
    else:
        ssh_command = f"ssh -T {node} {' '.join(command)}"
    try:
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
                if returncode == 0:
                    result_message = f"Command executed successfully."
                else:
                    os.makedirs(err_dir, exist_ok=True)
                    err_path = os.path.join(err_dir, f"{node}.err")

                    with open(err_path, 'w') as err_file:
                        err_file.write(stderr)

                    result_message = f"ERROR!! Stderr saved to: {err_path}"

            elif err_dir is None:  # only --out
                if returncode == 0:
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, f"{node}.out")

                    with open(out_path, 'w') as out_file:
                        out_file.write(stdout)
                    result_message = f"Success!! Result saved to: {out_path}"

                else:
                    result_message = f"Error executing command."

            else:  # --out --err
                if returncode == 0:
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, f"{node}.out")

                    with open(out_path, 'w') as out_file:
                        out_file.write(stdout)

                    result_message = f"Success!! Result saved to: {out_path}"
                else:
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
    results = {}  # 각 노드의 결과를 저장할 딕셔너리
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
            # 결과를 딕셔너리에 저장
            results[node] = output_str

    # 각 노드의 결과를 묶어서 출력
    print("------------------------")
    for node, result in results.items():
        print(result, end="")
    print("-------------------------")


def process_input(command, nodes, out_dir, err_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 각 노드에 대한 worker 함수를 스레드 풀에서 실행
        futures = [executor.submit(
            worker, node, command, out_dir, err_dir) for node in nodes]

        # Future의 결과를 가져와 출력 큐에 넣음
        for future in concurrent.futures.as_completed(futures):
            output_queue.put(future.result())

    # 모든 worker 스레드 종료 후에 None 큐에 넣음
    output_queue.put(None)

    # 스레드의 결과를 출력
    print_output()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostlist', type=str, default=None)
    parser.add_argument('--hostfile', type=str, required='-i' in sys.argv, default=None)
    parser.add_argument('--out', type=str, default=None)
    parser.add_argument('--err', type=str, default=None)
    parser.add_argument('command', type=str, nargs='*', default=None)
    parser.add_argument('-i', action='store_true')  # 대화식 모드 플래그
    args, remaining_args = parser.parse_known_args()

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

    # interactive mode에서는 --hostfile이 반드시 필요한 경우에만 명령을 처리
    if args.i and not args.hostfile:
        print("Error: '--hostfile' is required in interactive mode.")
        return

    if args.i:
        print(f"Enter 'quit' to leave this interactive mode. Working with nodes: {', '.join(get_node_names())}")
        while True:
            try:
                user_input = input("clsh> ")
                if user_input.lower() == 'quit':
                    break

                # Check for local command
                if user_input.startswith('!'):
                    local_command = user_input[1:]
                    local_process = subprocess.Popen(
                        local_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                        text=True
                    )
                    local_stdout, local_stderr = local_process.communicate()
                    print("LOCAL:", local_stdout)
                    print(local_stderr, end="")
                else:
                    # Remote command
                    if args.hostfile:  # interactive 모드에서는 --hostfile이 필요한 경우에만 처리
                        with input_lock:  # Lock to synchronize input
                            # 호스트 파일에서 호스트 이름을 읽어오기
                            with open(args.hostfile, 'r') as hostfile:
                                nodes = hostfile.read().splitlines()

                            command_tokens = shlex.split(user_input)

                            # 각 노드에 대한 ssh 명령 작성 및 실행
                            for node in nodes:
                                ssh_command = f"ssh -T {node} {' '.join(command_tokens)}"
                                process = subprocess.Popen(
                                    ssh_command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    shell=True,
                                    text=True
                                )
                                stdout, stderr = process.communicate()
                                print(f"{ssh_command}: {stdout}")
                                print(stderr, end="")

            except EOFError:
                break
    else:
        # Non-interactive mode
        try:
            print("non-interactive!")
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

            command = args.command
            if args.command == []:
                print(f"Switching to interactive mode. Working with nodes: {', '.join(get_node_names())}")
                user_input = input("clsh> ").split()
                print(f"user_input : {user_input}")
                command = user_input

            
            out_dir = args.out if args.out else None
            err_dir = args.err if args.err else None

            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 각 노드에 대한 worker 함수를 스레드 풀에서 실행
                futures = [executor.submit(
                    worker, node, command, out_dir, err_dir) for node in nodes]

                # Future의 결과를 가져와 출력 큐에 넣음
                for future in concurrent.futures.as_completed(futures):
                    output_queue.put(future.result())

            # 모든 worker 스레드 종료 후에 None 큐에 넣음
            output_queue.put(None)

            # 스레드의 결과를 출력
            print_output()

        except ValueError as e:
            print(str(e))

if __name__ == "__main__":
    main()


