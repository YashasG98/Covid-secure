# Covid_Secure

A web app to track the population density of places to stay safe .

### Setting up MySQL 
```bash
sudo apt install mysql-server libmysqlclient-dev
sudo mysql_secure_installation
mysql -u root -p
#enter your password when prompted
mysql > source db_config.sql 
mysql > quit
exit
```

### Setting up Virtual Environment and Install Requirements
```bash
sudo pip install virtualenv
python3 -m venv flaskenv
source flaskenv/bin/activate
pip install -r requirements.txt
```

### Running the project

Change your  mysql root password in server.py line 10.

```bash
python server.py
```
