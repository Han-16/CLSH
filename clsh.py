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

    
def run_command(container_name, command, out_dir=None, err_dir=None):
    try:
        # SSH를 통해 도커 컨테이너에서 명령어를 실행하고 결과를 파이프로 받아옴
        ssh_command = f"docker exec {container_name} {' '.join(command)}"
        process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        # 결과를 각 노드의 파일에 저장
        if out_dir and err_dir:
            # 디렉토리가 존재하지 않으면 생성
            os.makedirs(out_dir, exist_ok=True)
            os.makedirs(err_dir, exist_ok=True)

            out_path = os.path.join(out_dir, f"{container_name}.out")
            err_path = os.path.join(err_dir, f"{container_name}.err")

            # 파일이 이미 존재하면 내용을 지우고, 없으면 새로 생성
            with open(out_path, 'w') as out_file:
                out_file.write(stdout)

            with open(err_path, 'w') as err_file:
                err_file.write(stderr)

        if process.returncode == 0:
            return container_name, f"Command executed successfully. Stdout saved to: {out_path}" if out_dir else stdout.strip()
        else:
            return container_name, f"Error executing command on {container_name}. Stderr saved to: {err_path}" if err_dir else f"Error executing command on {container_name}: {stderr.strip()}"
    except Exception as e:
        return container_name, f"Error executing command on {container_name}: {str(e)}"


def execute_commands(container_names, command, out_dir=None, err_dir=None):
    # ThreadPoolExecutor를 사용하여 각 컨테이너에 대한 명령을 병렬로 실행
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_command, container_name, command, out_dir, err_dir): container_name for container_name in container_names}

        # 결과를 수집하면서 순서대로 출력
        for future in concurrent.futures.as_completed(futures):
            container_name = futures[future]
            try:
                result = future.result()
                print(f"{result[0]}: {result[1]}")
            except Exception as e:
                print(f"Error for {container_name}: {str(e)}")

def main():
    # ArgumentParser 객체로 명령행 인수  설정을 추가
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostfile', type=str, default=None)
    parser.add_argument('--out', type=str, default=None)
    parser.add_argument('--err', type=str, default=None)
    parser.add_argument('command', type=str, nargs='+')
    
    # parse_args를 호출하여 명령행 인수를 파싱하고, 결과를 args에 저장
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

    # --out 및 --err 옵션을 사용했을 때 출력 디렉토리를 지정
    out_dir = args.out if args.out else None
    err_dir = args.err if args.err else None
    print(f"out_dir: {out_dir}")

    # execute_commands 함수를 호출하여 명령을 실행합니다.
    execute_commands(container_names, args.command, out_dir, err_dir)

if __name__ == "__main__":
    main()
