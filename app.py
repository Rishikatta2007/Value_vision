from flask import Flask, render_template, request, redirect, flash, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pandas as pd
import numpy as np
import pickle as pk
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Flask app setup
app = Flask(__name__)
app.secret_key = 'rishi12345'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'tiger'
app.config['MYSQL_DB'] = 'user_database'
mysql = MySQL(app)

# Load ML models and scalers
loan_model = pk.load(open('loan_model.pkl', 'rb'))
loan_scaler = pk.load(open('scaler.pkl', 'rb'))
credit_model = pk.load(open('credit_score.pkl', 'rb'))

# Email configuration (for feedback)
EMAIL_ADDRESS = 'rishikeshkatta2007@gmail.com'
EMAIL_PASSWORD = '9029615480@Rishi'

# Decorator to require login for specific routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Route: Home Page
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/get_started')
def gwtstarted():
    return render_template('selection.html')

# Route: Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    return render_template('login.html')

# Route: Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password == confirm_password:
            hashed_password = generate_password_hash(password)
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', 
                           (username, hashed_password))
            mysql.connection.commit()
            cursor.close()
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match. Please try again.', 'danger')
    return render_template('signup.html')

# Route: Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# Route: Loan Prediction
@app.route('/loan_predict', methods=['GET', 'POST'])
@login_required
def loan_predict():
    if request.method == 'POST':
        try:
            # Get form data and preprocess it
            no_of_dep = int(request.form['no_of_dep'])
            grad = 0 if request.form['grad'] == 'Graduated' else 1
            self_emp = 0 if request.form['self_emp'] == 'No' else 1
            Annual_Income = float(request.form['Annual_Income'])
            Loan_Amount = float(request.form['Loan_Amount'])
            Loan_Dur = float(request.form['Loan_Dur'])
            Cibil = float(request.form['Cibil'])
            Assets = float(request.form['Assets'])

            # Create input array and predict
            pred_data = pd.DataFrame([[no_of_dep, grad, self_emp, Annual_Income, 
                                       Loan_Amount, Loan_Dur, Cibil, Assets]],
                                     columns=['no_of_dependents', 'education', 'self_employed', 
                                              'income_annum', 'loan_amount', 'loan_term', 
                                              'cibil_score', 'Assets'])
            pred_data = loan_scaler.transform(pred_data)
            prediction = "Loan Approved" if loan_model.predict(pred_data)[0] == 1 else "Loan Rejected"
            return render_template('loan_result.html', prediction=prediction)
        except Exception as e:
            flash(f"Error during prediction: {str(e)}", 'danger')
    return render_template('loan_form.html')

# Route: Credit Score Prediction
@app.route('/credit_predict', methods=['GET', 'POST'])
@login_required
def credit_predict():
    if request.method == 'POST':
        try:
            # Get form data for credit prediction
            features = np.array([[float(request.form[field]) for field in [
                'annual_income', 'monthly_salary', 'bank_accounts', 'credit_cards', 
                'interest_rate', 'loans', 'avg_days_delayed', 'delayed_payments', 
                'credit_mix', 'outstanding_days', 'credit_history_age', 'emi', 
                'investment', 'monthly_balance']]])
            prediction = credit_model.predict(features)[0]
            return render_template('result_credit.html', prediction=prediction)
        except Exception as e:
            flash(f"Error during prediction: {str(e)}", 'danger')
    return render_template('credit_score.html')

# Function: Send Email Feedback (Optional)
def send_email(name, email, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS
        msg['Subject'] = f'Feedback from {name}'
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Error sending email: {str(e)}")

# Route: Contact Page with Feedback Form
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Store feedback in MySQL database
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO feedback (name, email, message) VALUES (%s, %s, %s)', 
                       (name, email, message))
        mysql.connection.commit()
        cursor.close()

        # Optional: Send email notification only if feedback is saved
        send_email(name, email, message)

        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')



# Main entry point
if __name__ == '__main__':
    app.run(debug=True)
