from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re, auth
from datetime import date

app = Flask(__name__)

app.secret_key = 'your secret key'

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '**********'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_DB'] = 'bidding_website'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/addcrop', methods =['GET', 'POST'])
def add_crop():
    msg=''
    if request.method == 'POST':
        crop = request.form['crop']
        quantity = request.form['quantity']
        price = request.form['price']
        date = request.form['date']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT crop_id FROM crop WHERE crop_name = %s', (crop,))
        crop_id = cursor.fetchone()

        cursor.execute('''INSERT INTO add_crop(crop_id,quantity,price,datee,farmer_id) 
                          VALUES (%s, %s, %s, %s, %s)''' , 
                          (crop_id['crop_id'], quantity, price, date, session['id']))
        mysql.connection.commit()

        cursor.execute('SELECT add_id FROM add_crop ORDER BY add_id')
        add = cursor.fetchall()

        cursor.execute('INSERT INTO bidding(add_id,time_left,last_bid_amount)VALUES(%s, %s, %s)',(add[-1]['add_id'],date,price,))
        mysql.connection.commit()

        msg = "Crop added!"

    return render_template('add_crop.html',msg=msg)

@app.route('/demandcrop', methods =['GET', 'POST'])
def demand_crop():
    if request.method == 'POST':
        crop = request.form['crop']
        quantity = request.form['quantity']
        datee = date.today()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT crop_id FROM crop WHERE crop_name = %s', (crop,))
        crop_id = cursor.fetchone()

        cursor.execute('''INSERT INTO demand_crop(crop_id,quantity,datee,consumer_id) 
                          VALUES (%s, %s, %s, %s)''' , 
                          (crop_id['crop_id'], quantity, datee, session['id']))
        mysql.connection.commit()

    return render_template('demand_crop.html')


@app.route("/demandlist",)
def demandlist():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM demand_crop as d join crop as c on c.crop_id = d.crop_id order by datee')
    account = cursor.fetchall()

    return render_template('demandlist.html',account=account)

@app.route("/feedback",)
def feedback():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT * from feedback
                      join bidding on bidding.bidding_id = feedback.bidding_id 
                      join add_crop on add_crop.add_id = bidding.add_id
                      join crop on crop.crop_id = add_crop.crop_id
                      where farmer_id = %s''',(session['id'],))
    account = cursor.fetchall()

    return render_template('feedback.html',account=account)

@app.route("/yourcrops",)
def yourcrops():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT *
                      FROM bidding as b join add_crop as a 
                      on b.add_id = a.add_id join crop as c 
                      on c.crop_id = a.crop_id
                      left outer join consumer as d 
                      on d.consumer_id = b.last_bidder
                      where farmer_id = %s
                      ORDER BY datee''', (session['id'],))
    account = cursor.fetchall()

    return render_template('yourcrops.html',account=account)

@app.route("/yourdemands",)
def yourdemands():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT *
                      FROM demand_crop as d join crop as c
                      on d.crop_id = c.crop_id
                      WHERE consumer_id = %s
                      ORDER BY datee''', (session['id'],))
    account = cursor.fetchall()

    return render_template('yourdemands.html',account=account)


@app.route("/finalbid", methods =['GET', 'POST'])
def finalbid():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    datee = date.today()
    feedback = []

    if 'occupation' in session:
        cursor.execute('''SELECT *
                          FROM bidding as b join add_crop as a 
                          on b.add_id = a.add_id join crop as c 
                          on c.crop_id = a.crop_id
                          left outer join consumer as d
                          on d.consumer_id = b.last_bidder
                          where farmer_id = %s
                          and time_left < %s''',(session['id'],datee,))
        account = cursor.fetchall()
    else:
        cursor.execute('''SELECT *
                          FROM bidding as b join add_crop as a 
                          on b.add_id = a.add_id join crop as c 
                          on c.crop_id = a.crop_id
                          left outer join farmer as f
                          on f.farmer_id = a.farmer_id
                          where last_bidder = %s
                          and time_left < %s''',(session['id'],datee,))
        account = cursor.fetchall()

    cursor.execute('''SELECT * from feedback''')
    gg = cursor.fetchall()
    for x in range(len(gg)):
      feedback.append(gg[x]['bidding_id'])

    if request.method == 'POST':
      bidid = request.form['bid_id']
      message = request.form['message-text']
      rating = request.form['rating']

      cursor.execute('''INSERT INTO feedback(comment,rating,bidding_id) 
                        VALUES (%s, %s, %s)''' , 
                        (message,rating,bidid))
      mysql.connection.commit()


    return render_template('finalbid.html',account=account,feedback=feedback)

@app.route('/bidding', methods =['GET', 'POST'])
def bidding():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT *
                      FROM bidding as b join add_crop as a 
                      on b.add_id = a.add_id join crop as c 
                      on c.crop_id = a.crop_id
                      order by time_left''')
    account = cursor.fetchall()
    datee = date.today()

    if request.method == 'POST':
        current_bid = request.form['bid']
        bid_id = request.form['bid_id']

        cursor.execute('SELECT * FROM bidding WHERE bidding_id = %s', (bid_id,))
        select = cursor.fetchone()


        if int(current_bid) > int(select['last_bid_amount'] or 0):
            cursor.execute('''UPDATE bidding 
                              SET last_bid_amount = %s, last_bidder = %s
                              WHERE bidding_id = %s''', (current_bid,session['id'],bid_id,))
            mysql.connection.commit()
            return redirect(url_for('bidding'))
        else:
            msg = 'Your bid should be higher than last bid!'

    return render_template('bidding.html',account=account,datee=datee)

@app.route('/profile', methods =['GET', 'POST'])
def profile():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM farmer WHERE farmer_id = %s', (session['id'],))
    account1 = cursor.fetchone()
    cursor.execute('SELECT * FROM consumer WHERE consumer_id = %s', (session['id'],))
    account2 = cursor.fetchone()
    if account1 or account2:
        return redirect(url_for('home'))

    if request.method == 'POST':
        fullname = request.form['fullname']
        pan_no = request.form['panno']
        street_no = request.form['streetno']
        zip_code = request.form['zipcode']
        occupation = request.form['occupation']
        phoneno = request.form['phoneno']
        phoneno2 = request.form['phoneno2']

        if occupation == 'Farmer':
            cursor.execute('INSERT INTO farmer VALUES (%s, %s, %s, %s, %s)' , (session['id'], pan_no, fullname, street_no, zip_code))
            cursor.execute('INSERT INTO farmer_no VALUES (%s,%s)',(session['id'],phoneno))
            if phoneno2:
              cursor.execute('INSERT INTO farmer_no VALUES (%s,%s)',(session['id'],phoneno2))
            mysql.connection.commit()
            session['occupation'] = 'Farmer'
            return redirect(url_for('home'))
        else:
            cursor.execute('INSERT INTO consumer VALUES (%s, % s, % s, % s, % s, %s)', (session['id'],occupation, pan_no, fullname, street_no, zip_code,))
            cursor.execute('INSERT INTO consumer_no VALUES (%s,%s)',(session['id'],phoneno))
            if phoneno2:
              cursor.execute('INSERT INTO consumer_no VALUES (%s,%s)',(session['id'],phoneno2))
            mysql.connection.commit()
            return redirect(url_for('home'))

    return render_template('profile.html')

@app.route('/register', methods =['GET', 'POST'])
def register():
    if 'loggedin' in session:
        return render_template('home.html')
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form : 
        username = request.form['username'] 
        password = request.form['password'] 
        email = request.form['email']
        dob = request.form['dob'] 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute('SELECT * FROM login WHERE username = %s', (username,)) 
        account = cursor.fetchone() 
        if account: 
            msg = 'Account already exists !'
        else: 
            cursor.execute('INSERT INTO login (email,username,password,dob) VALUES (% s, % s, % s, %s)', (email, username, password, dob,)) 
            mysql.connection.commit()
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods =['GET', 'POST']) 
def login():
    if 'loggedin' in session:
        return render_template('home.html')
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form: 
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute('SELECT * FROM login WHERE email = %s AND password = %s', (email, password)) 
        account = cursor.fetchone()
        if account: 
            session['tryloggedin'] = True
            session['id'] = account['login_id'] 
            session['username'] = account['username']

            cursor.execute('SELECT * FROM farmer WHERE farmer_id = %s', (session['id'],))
            session['occupation'] = cursor.fetchone()
            if not session['occupation']:
                session.pop('occupation')

            return redirect(url_for('otp')) 
        else: 
            msg = 'Incorrect email / password !'
    return render_template('login.html', msg = msg)

@app.route("/otp", methods =['GET', 'POST'])
def otp():
    if 'loggedin' in session:
        return redirect(url_for('home'))
    if 'tryloggedin' not in session:
        return redirect(url_for('login'))

    key = session['username'].encode('utf-8')
    print(auth.TOTP(key))

    if request.method == 'POST':
        totp = request.form['totp']

        if totp == auth.TOTP(key):
            session['loggedin'] = True
            return redirect(url_for('profile'))
        else:
            msg = 'Incorrect hotp / totp !'
            return render_template('otp.html', msg = msg)
    return render_template('otp.html')

@app.route("/logout")
def logout():
   session.pop('loggedin', None)
   session.pop('tryloggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   return redirect(url_for('home'))

@app.route("/tryagain")
def tryagain():
    return redirect(url_for('otp'))

if __name__ == '__main__':
	app.run(debug=True)