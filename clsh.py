import argparse
import concurrent.futures
import subprocess
import os


def get_container_names():
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


def run_command(container_name, command):
    try:
        # SSH를 통해 도커 컨테이너에서 명령어를 실행하고 결과를 파이프로 받아옴
        ssh_command = f"docker exec {container_name} {' '.join(command)}"
        process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return container_name, stdout.strip()
        else:
            return container_name, f"Error executing command on {container_name}: {stderr.strip()}"
    except Exception as e:
        return container_name, f"Error executing command on {container_name}: {str(e)}"


def execute_commands(container_names, command):
    # ThreadPoolExecutor를 사용하여 각 컨테이너에 대한 명령을 병렬로 실행
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_command, container_name, command): container_name for container_name in
                   container_names}

        # 결과를 수집하면서 순서대로 출력
        for future in concurrent.futures.as_completed(futures):
            container_name = futures[future]
            try:
                result = future.result()
                print(f"{result[0]}: {result[1]}")
            except Exception as e:
                print(f"Error for {container_name}: {str(e)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostfile', type=str, default=None)  # --hostfile 옵션을 생략할 경우를 위해 default=None으로 설정
    parser.add_argument('command', type=str, nargs='+')
    args = parser.parse_args()

    if args.hostfile is None:
        # --hostfile 옵션이 제공되지 않은 경우, 환경 변수 및 기본 파일에서 호스트 정보 읽어오기
        try:
            container_names = get_container_names()
        except ValueError as e:
            print(f"Error: {str(e)}")
            return
    else:
        # --hostfile 옵션이 제공된 경우 해당 파일에서 호스트 정보 읽어오기
        with open(args.hostfile, 'r') as f:
            container_names = f.read().splitlines()

    execute_commands(container_names, args.command)


if __name__ == "__main__":
    main()
