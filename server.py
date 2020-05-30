from flask import Flask,render_template,request,redirect, url_for, make_response
from flask_mysqldb import MySQL
import math, time, datetime

app = Flask(__name__)
app.config.from_object('config.Config')

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Game_server'     #change this password to your MySQL password for root@localhost 
app.config['MYSQL_DB'] = 'Covid_secure'

mysql = MySQL(app)
outsideDistThreshold = 0.5
populationDensityThreshold = 2
safety_time = 2

logged_in_users =[]

# App functionality
@app.route('/')
def Home():
    resp = make_response(render_template('login.html'))
    email = request.args.get('email')
    if email in logged_in_users:
        logged_in_users.remove(email)
    return resp        

@app.route('/register.html',methods = ['GET','POST'])
def Register():
    error = None
    if request.method=='POST':
        email=request.form['registerEmail']
        password=request.form['registerPassword']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        homeLat = request.form['homeLat']
        homeLong = request.form['homeLong']

        #Valid input check
        if(len(email) is 0):
            error = 'Email cannot be empty'
            return render_template('register.html', error = error)
        if (len(password) < 8):
            error = 'Password must be 8 characters long'
            return render_template('register.html', error = error)
        if (len(firstName) is 0):
            error = 'First Name cannot be empty'
            return render_template('register.html', error = error)
        
        #Valid input handling
        cur=mysql.connection.cursor()
        _sql = "select * from Login_Credentials where UserID = '{0}'"
        cur.execute(_sql.format(email))
        data=cur.fetchall()
        if(len(data) is 0):
            error = None
            cur.execute("INSERT INTO User_Profile(UserID,firstName,lastName,homeLat,homeLong) VALUES(%s,%s,%s,%s,%s)",(email,firstName,lastName,float(homeLat),float(homeLong)))
            cur.execute("INSERT INTO Login_Credentials VALUES(%s,MD5(%s))",(email,password))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('Login'))
        else:
            error = 'Email already registered!'
    return render_template('register.html', error = error)

@app.route('/login.html', methods = ['GET', 'POST'])
def Login():
    error = None
    if request.method=='POST':
        email=request.form['loginEmail']
        password=request.form['loginPassword']
        cur=mysql.connection.cursor()
        _sql = "select md5('{0}')"
        cur.execute(_sql.format(password))
        enc_string=cur.fetchall()
        _sql = "select password from Login_Credentials where UserID = '{0}'"
        cur.execute(_sql.format(email))
        stored=cur.fetchall()
        if(len(stored) is 0):
            error = 'Email not found!'
        else:
            if(enc_string==stored):
                logged_in_users.append(email)
                resp = make_response(redirect(url_for('Index')))
                resp.set_cookie('email',email)
                cur.close()
                return resp
            else:
                error = 'Invalid password'
    return render_template('login.html', error = error)


@app.route('/index.html', methods = ['GET', 'POST'])
def Index():
    email = request.cookies.get('email')
    currLat=None
    currLong=None
    if email in logged_in_users:
        cur=mysql.connection.cursor()
        _sql = "select lastLat, lastLong from Last_Location where UserID = '{0}'"
        cur.execute(_sql.format(email))
        stored=cur.fetchall()
        if(len(stored)!=0):
            currLat=stored[0][0]
            currLong=stored[0][1]
        if request.method == 'POST':
            arr = change_coordinates_and_check_density(cur, email)
            if(arr[0] is 1):
                currLat=arr[1]
                currLong=arr[2]
        return render_template('index.html', email=email,currLat=currLat,currLong=currLong)
    else:
        return redirect(url_for('Login'))

@app.route('/check.html', methods = ['GET', 'POST'])
def check_location():
    check=None
    email = request.cookies.get('email')
    flagged_users = None
    total_users = None
    if email in logged_in_users:
        if request.method == 'POST':
            arr = find_people(float(request.form['checkLat']),float(request.form['checkLong']),float(request.form['time']))
            flagged_users = arr[0]
            total_users = arr[1]
        return render_template('check.html', email=email,flagged_users= flagged_users,total_users= total_users)
    else:
        return redirect(url_for('Login'))

def change_coordinates_and_check_density(cur, email):
    currLatitude = request.form['currLat']
    currLongitude = request.form['currLong']
    _sql = "select homeLat, homeLong from User_Profile where UserID = '{0}'"
    cur.execute(_sql.format(email))
    stored=cur.fetchall()
    if calculate_dist(stored[0][0],stored[0][1],float(currLatitude), float(currLongitude))>outsideDistThreshold:
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("select count(*) from Last_Location")
        id = cur.fetchall()
        cur.execute("INSERT INTO Last_Location(LocationID,UserID,lastLat,lastLong,updated_at) VALUES(%s,%s,%s,%s,%s)",(id[0][0]+1,email,float(currLatitude),float(currLongitude),timestamp))
        mysql.connection.commit()
        cur.execute("SELECT UserID, MAX(LocationID) AS location_id FROM Last_Location GROUP BY UserID DESC;")
        data = cur.fetchall()
        areaCount = 0
        areaUserIDs = []
        for i in range(0,len(data)):
            _sql = "select lastLat, lastLong, updated_at from Last_Location where LocationID = '{0}'"
            cur.execute(_sql.format(data[i][1]))
            stored=cur.fetchall()
            t_new = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            t_old = datetime.datetime.strptime(stored[0][2].strftime('%Y-%m-%d %H:%M:%S'), "%Y-%m-%d %H:%M:%S")
            difference = t_new - t_old
            if difference.seconds < safety_time*60*60:
                if calculate_dist(stored[0][0],stored[0][1],float(currLatitude), float(currLongitude))<=outsideDistThreshold:
                    areaCount+=1
                    areaUserIDs.append(data[i][0])
        if(areaCount>=populationDensityThreshold):
            for i in range(0,len(areaUserIDs)):
                _sql="update User_Profile set flag = 1 where UserID='{0}'"
                print(_sql.format(areaUserIDs[i]))
                cur.execute(_sql.format(areaUserIDs[i]))
                mysql.connection.commit()
        cur.close()
        currLat=currLatitude
        currLong=currLongitude
        return [1,currLat,currLong]
    return [0]

def find_people(checkLat,checkLong,time_check):
    cur=mysql.connection.cursor()
    cur.execute("SELECT UserID, MAX(LocationID) AS location_id FROM Last_Location GROUP BY UserID DESC;")
    data = cur.fetchall()
    areaUserIDs = []
    for i in range(0,len(data)):
        _sql = "select lastLat, lastLong, updated_at from Last_Location where LocationID = '{0}'"
        cur.execute(_sql.format(data[i][1]))
        stored=cur.fetchall()
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        t_new = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        t_old = datetime.datetime.strptime(stored[0][2].strftime('%Y-%m-%d %H:%M:%S'), "%Y-%m-%d %H:%M:%S")
        difference = t_new - t_old
        if difference.seconds < time_check*60*60:
            if calculate_dist(checkLat,checkLong,stored[0][0],stored[0][1])<=outsideDistThreshold:
                areaUserIDs.append(data[i][0])
    flaggedUsers = 0
    for i in range(0,len(areaUserIDs)):
        _sql="SELECT flag from User_Profile where UserID='{0}'"
        print(_sql.format(areaUserIDs[i]))
        cur.execute(_sql.format(areaUserIDs[i]))
        data = cur.fetchall()   
        if(data[0][0]==1):
            flaggedUsers+=1
    return [flaggedUsers,len(areaUserIDs)]


def calculate_dist(lat_a,long_a,lat_b,long_b):
    R = 6373.0
    lat1 = math.radians(lat_a)
    lon1 = math.radians(long_a)
    lat2 = math.radians(lat_b)
    lon2 = math.radians(long_b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

if __name__ == "__main__":
    app.run(port=3000)