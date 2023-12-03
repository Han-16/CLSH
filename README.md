# CLSH 구현하기

## 원격의 다수의 쉘에 명령어 실행하고, 결과 수집하여 출력하기

### 사용 예시 (1)
node1, node2, node3, node4 의 /proc/loadavg 읽어오기
```
$ clsh -h node1,node2,node3,node4 cat /proc/loadavg
```
 

### 사용 예시 (2)
호스트파일에 저장하여 사용하기
```
$ clsh --hostfile ./hostfile cat /proc/loadavg
```

```
$ cat ./hostfile
node1
node2
node3
node4
```


# 옵션1  
--hostfile 옵션을 생략할 경우의 동작
1. CLSH_HOSTS 환경 변수에서 호스트이름 읽어오기, 콜론(:)으로 구분
2. CLSH_HOSTFILE 환경 변수에서 파일이름 읽어오기
    - 기본은 상대경로로 처리, /로 시작하는 경우 절대 경로로도 처리 
3. 현재 디렉토리에서 .hostfile 에서 읽어오기
4. 위의 모든 것을 실패할 경우 에러 처리


## 1. CLSH_HOSTS 환경 변수에서 호스트이름 읽어오기, 콜론(:)으로 구분
예시<br/>
```
export CLSH_HOSTS=node1:node12:node30
```
```clsh cat /proc/loadavg
Note: use CLSH_HOSTS environment
node1: ...
node12: ...
node30: ...
```

## 2. CLSH_HOSTFILE 환경 변수에서 파일이름 읽어오기

예시<br/>
```
export CLSH_HOSTFILE=clsuterfile
```
```
clsh cat /proc/loadavg
Note: use hostfile ‘clusterfile’ (CLSH_HOSTFILE env) 
node1: ...
node12: ...
node30: ...
```

## 3. 현재 디렉토리에서 .hostfile 에서 읽어오기

예시<br/>
```
clsh cat /proc/loadavg
Note: use hostfile ‘.hostfile’ (default) 
node1: ...
node12: ...
node30: ...
```

## 4. 위의 모든 것을 실패할 경우 에러 처리

- CLSH_HOSTS 환경 변수가 없는 경우 
    - CLSH_HOSTFILE 환경 변수 검사, 없는 경우 
    - .hostfile 검사 없는 경우

- “--hostfile 옵션이 제공되지 않았습니다” 라는 에러 문구 출력 후 종료 



# 옵션 2
쉘 Redirection 구현하기

```
$ ls /etc/*.conf | clsh --hostfile ./hostfile -b xargs ls
```
ls 의 결과를 clsh 로 전달하여 원격 실행하게 하기