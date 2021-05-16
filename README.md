# whosfault

## Introduction
League of Legend 라는 게임을 하다 보면 팀원들이 못해서 지는 경우가 많습니다.
그런데 정말 팀원 때문일까요?
whosfault는 누구 때문에 게임이 졌는지 분석하는 롤 전적서비스 입니다.


## frontend
![image](https://user-images.githubusercontent.com/59424336/111421448-55a52b80-8730-11eb-81a3-cefa6bf66b6b.png)
React

## Backend
Django
### Message broker
Redis 기반




### Worker
Celery


```
sudo apt-get update
sudo apt install python3-pip
sudo pip3 install virtualenv
sudo apt install python3.7
virtualenv --python=python3.7 virtual

sudo apt-get install npm
sudo npm cache clean -f
sudo npm install -g n
sudo n stable # updating nodejs to newer version
sudo apt-get install npm
sudo npm install -g yarn
sudo npm install -g create-react-app
```

```
git clone & cd
backend > pip install -r requirements
sudo apt-get update
sudo apt-get install mysql-server
sudo apt-get install libmysqlclient-dev
sudo apt-get install python3.7-dev
sudo mysql -u root -p
CREATE DATABASE mydb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
create user 'who'@'%' identified by [password];
grant all on mydb.* to 'who'@'%';
flush privileges;
```
```
celery -A backend beat -l info 
celery -A backend worker -l info 
```
