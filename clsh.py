# import argparse
# import subprocess
#
# def run_command(host, command):
#     try:
#         # SSH를 통해 도커 컨테이너에서 명령어를 실행하고 결과를 파이프로 받아옴
#         ssh_command = f"ssh {host} docker exec {host} {' '.join(command)}"
#         process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#         stdout, stderr = process.communicate()
#
#         if process.returncode == 0:
#             return host, stdout.strip()
#         else:
#             return host, f"Error executing command on {host}: {stderr.strip()}"
#     except Exception as e:
#         return host, f"Error executing command on {host}: {str(e)}"
#
# def main():
#     parser = argparse.ArgumentParser(description="Run commands on multiple Docker containers via SSH")
#     parser.add_argument('--hostfile', type=str, required=True)
#     parser.add_argument('command', type=str, nargs='+')
#     args = parser.parse_args()
#
#     with open(args.hostfile, 'r') as f:
#         hosts = f.read().splitlines()
#
#     # 각 호스트에 대해 명령을 실행하고 결과를 출력
#     for host in hosts:
#         result = run_command(host, args.command)
#         print(f"{result[0]}: {result[1]}")
#
# if __name__ == "__main__":
#     main()


import argparse
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

def main():
    parser = argparse.ArgumentParser(description="Run commands on multiple Docker containers via SSH")
    parser.add_argument('--hostfile', type=str, required=True)
    parser.add_argument('command', type=str, nargs='+')
    args = parser.parse_args()

    with open(args.hostfile, 'r') as f:
        container_names = f.read().splitlines()

    # 각 컨테이너에 대해 명령을 실행하고 결과를 출력
    for container_name in container_names:
        result = run_command(container_name, args.command)
        print(f"{result[0]}: {result[1]}")

if __name__ == "__main__":
    main()
