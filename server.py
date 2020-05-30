from flask import Flask,render_template,request,redirect, url_for, make_response
from flask_mysqldb import MySQL
import math, time, datetime
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config.from_object('config.Config')

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'     #change this password to your MySQL password for root@localhost 
app.config['MYSQL_DB'] = 'Covid_secure'

mysql = MySQL(app)
outsideDistThreshold = 0.5

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
            currLatitude = request.form['currLat']
            currLongitude = request.form['currLong']
            _sql = "select homeLat, homeLong from User_Profile where UserID = '{0}'"
            cur.execute(_sql.format(email))
            stored=cur.fetchall()
            if calculate_dist(stored[0][0],stored[0][1],float(currLatitude), float(currLongitude))>outsideDistThreshold:
                ts = time.time()
                timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                cur.execute("INSERT INTO Last_Location(UserID,lastLat,lastLong,updated_at) VALUES(%s,%s,%s,%s)",(email,float(currLatitude),float(currLongitude),timestamp))
                mysql.connection.commit()
                cur.close()
                currLat=currLatitude
                currLong=currLongitude
                trend(currLat,currLong)               
        return render_template('index.html', email=email,currLat=currLat,currLong=currLong)
    else:
        return redirect(url_for('Login'))

@app.route('/check.html')
def check_location():
    check=None
    email = request.cookies.get('email')
    if email in logged_in_users:
        homeLat = request.form['checkLat']
        homeLong = request.form['checkLong']
        return render_template('check.html', email=email)
    else:
        return redirect(url_for('Login'))
def trend(lat,lng):
    lat=float(lat)
    lng = float(lng)
    cur=mysql.connection.cursor()
    _sql = "select * from last_location;"
    cur.execute(_sql)
    stored=cur.fetchall()
    if len(stored)==0:
        print("No users in past 24 hours near this location.")
    else:
        hour_collection = [set() for i in range(24)]
        for user,lat1,lng1,time in stored:
            if calculate_dist(lat1,lng1,lat,lng)< Area_considered:
                t=(time-datetime.datetime.now()).seconds
                if t < 24*3600:
                    hour_collection[t//3600].add(user)
        hour_collection = [len(i) for i in hour_collection]
        labels = [(datetime.now() - timedelta(hours = i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(24)]
        import matplotlib.pyplot as plt
        plt.figure(figsize=(20,5))
        labels = [(datetime.datetime.now() - datetime.timedelta(hours = i)).strftime('%H:%M') for i in range(24)]
        plt.plot(range(24),hour_collection)
        plt.ylabel("Number of people")
        plt.xlabel( "Time in past 24 hours")
        plt.xticks(range(24),labels = labels,rotation =0)
        plt.savefig(".\static\images\abc.jpg")

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
    app.run()
