import argparse
import concurrent.futures
import subprocess


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
    parser = argparse.ArgumentParser(description="Run commands on multiple Docker containers via SSH")
    parser.add_argument('--hostfile', type=str, required=True)
    parser.add_argument('command', type=str, nargs='+')
    args = parser.parse_args()

    with open(args.hostfile, 'r') as f:
        container_names = f.read().splitlines()

    execute_commands(container_names, args.command)


if __name__ == "__main__":
    main()
