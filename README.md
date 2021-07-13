# whosfault
http://www.whosfault.me/
(production API pending approval)

## Introduction
When playing a game called League of Legends, you often lose because your team members do not do well.
But is it really because of your team?
whosfault is a role statistics service that analyzes who lost a game.

## frontend
![image](https://user-images.githubusercontent.com/59424336/111421448-55a52b80-8730-11eb-81a3-cefa6bf66b6b.png)

The frontend is implemented based on React.

## Backend
A backend API is implemented based on Django. When a user's request comes in, it receives the user's information through the RIOT API, analyzes it, and returns it.
However, the RIOT API has a rate limit. Even if a large number of users connect at the same time, the rate limit is not exceeded. Message queue is implemented in Redis, and Celery fetches tasks from the queue and processes them at a rate that does not exceed the rate limit. The implementation structure is shown in the image below.

![image](https://user-images.githubusercontent.com/59424336/125446901-db8bb39b-d66e-4655-a8ca-30c258746530.png)



## How to deploy

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
