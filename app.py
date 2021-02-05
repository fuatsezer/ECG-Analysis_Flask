from flask import Flask,redirect,url_for,flash,render_template,request,abort,session
from urllib.parse import urlparse, urljoin
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager,UserMixin,login_user,login_required,logout_user,current_user
from werkzeug.security import generate_password_hash,check_password_hash
from wtforms import StringField,PasswordField,SubmitField,BooleanField
from flask_wtf import FlaskForm
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool,CustomJS
from bokeh.layouts import column,row
from bokeh.plotting import figure
from bokeh.models import SingleIntervalTicker,Select
from bokeh.models.widgets import RangeSlider
from bokeh.embed import json_item
from wtforms.validators import DataRequired,EqualTo,Email
from jinja2 import Template
import datetime
import numpy as np
import json
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message,Mail
import pandas as pd
from bokeh.events import MouseMove,Tap
from scipy.signal import hilbert
from scipy.signal import find_peaks
from bokeh.resources import CDN


app = Flask(__name__, instance_relative_config=False)
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'test354509@gmail.com'
app.config['MAIL_PASSWORD'] = 'GBfvdcsxaz123'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail=Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.session_protection ="strong"
login_manager.login_message = "Please login to access this page"
login_manager.login_message_category = "info"

app.config["SECRET_KEY"] = "mysecretkey"
app.config['SECURITY_PASSWORD_SALT'] = "mysecpasssalt"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db=SQLAlchemy(app)
global df   
def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email,salt=app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token,expiration=3600):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token,salt=app.config['SECURITY_PASSWORD_SALT'],
                                 max_age=expiration)
    except:
        return False
    return email


def send_email(to,subject,template):
    msg = Message(subject,recipients=[to],html=template,
                  sender= 'test354509@gmail.com')
    mail.send(msg)
class Doctor(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key=True)
    title_name = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True,nullable=False)
    password_hash = db.Column(db.String(128))
    registered_on = db.Column(db.DateTime,nullable=False)
    confirmed = db.Column(db.Boolean,nullable=False,default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    hospital_name = db.Column(db.String(128),nullable=False)
    patients = db.relationship("Patient",backref="doctor",lazy="dynamic")
    def find_by_email(cls,email):
        return cls.query.filter_by(email=email).first()
    
    
    def __init__(self,title_name,email,password,confirmed,confirmed_on,hospital_name):
        self.title_name = title_name
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.registered_on = datetime.datetime.now()
        self.confirmed = confirmed
        self.confirmed_on = confirmed_on
        self.hospital_name = hospital_name
        
    def check_password(self,password):
        return check_password_hash(self.password_hash, password)

class Patient(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True,nullable=False)
    password_hash = db.Column(db.String(128))
    registered_on = db.Column(db.DateTime,nullable=False)
    confirmed = db.Column(db.Boolean,nullable=False,default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    doctor_id = db.Column(db.Integer(),db.ForeignKey("doctor.id"))
    ecg_values = db.relationship("ECGDB",backref="patient",lazy="dynamic")
    def find_by_email(cls,email):
        return cls.query.filter_by(email=email).first()
    def __init__(self,name,email,password,confirmed,confirmed_on):
        self.name = name
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.registered_on = datetime.datetime.now()
        self.confirmed = confirmed
        self.confirmed_on = confirmed_on
    def check_password(self,password):
        return check_password_hash(self.password_hash, password)
    def __repr__(self):
        return self.name
    
class ECGDB(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    ecg_values = db.Column(db.Float)
    patient_id = db.Column(db.Integer(),db.ForeignKey("patient.id"))
    def __init__(self,ecg_values,patient_id=None):
        self.ecg_values = ecg_values
        
    def __repr__(self):
        return "{}".format(self.ecg_values)
    
db.create_all()

class ChangeHospitalForm(FlaskForm):
    hospital = StringField("New Hospital",validators=[DataRequired()])
    submit = SubmitField("Change")


class PasswordResetForm(FlaskForm):
    password = PasswordField("New Password",validators=[DataRequired()])
    submit = SubmitField("Reset")   
class ResetEmailForm(FlaskForm):
    email = StringField("Business Email",validators=[DataRequired(),Email()])
    submit = SubmitField("Enter")
    def check_email(self,field):
        return Doctor.query.filter_by(email=field.data).first()
 
class RegistrationForm(FlaskForm):
    title_name = StringField("Title and Full Name",validators=[DataRequired()])
    hospital_name = StringField("Your Hospital Name",validators=[DataRequired()])
    email = StringField("Business Email",validators=[DataRequired(),Email()])
    password = PasswordField("Password",validators=[DataRequired(),EqualTo("confirm",
                                                                               message="Password must match")])
    confirm = PasswordField("Repeat Password",validators=[DataRequired()])
    accept_tos = BooleanField("I accept the contract",validators=[DataRequired()])
    submit = SubmitField("Register")
    def check_email(self,field):
        return Doctor.query.filter_by(email=field.data).first()
class LoginForm(FlaskForm):
    email = StringField("Email",validators=[DataRequired(),Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    submit = SubmitField("Log in")
    def check_user(self,field,field2):
        user = Doctor.query.filter_by(email=field.data).first()
        if user is not None:
            if user.check_password(field2.data)==False:
                return True
            else: 
                return False
        else:
            return True
    def check_confirm(self,field):
        user = Doctor.query.filter_by(email=field.data).first()
        if user.confirmed:
            return False
        else: 
            return True
            
        


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc     
    
def ecg_processing(ecg_values):
    signal = pd.Series(ecg_values)
    analytic_signal = hilbert(signal)
    filtered_signal = pd.Series(analytic_signal)
    saniye = []
    for i in range(0,len(filtered_signal)):
        saniye.append((i/len(filtered_signal))*(len(filtered_signal)/360))
    df = pd.DataFrame({"Saniye":saniye,"EKG Filtered":filtered_signal,"ECG":ecg_values})
    peaks, _ = find_peaks(filtered_signal, height=-100)
    peaks_value=[]
    for i in peaks:
        peaks_value.append(filtered_signal[i])
    r_peaks, _ = find_peaks(filtered_signal, height=np.mean(peaks_value)+3*np.std(peaks_value))
    peaks, _ = find_peaks(filtered_signal, height=-100)
    trough, _ = find_peaks(-filtered_signal, height=0)
    peaks = np.concatenate([peaks,trough],axis = 0)
    peaks = sorted(peaks)
    for i in peaks:
        for z in r_peaks:
            if i == z:
                peaks.remove(i)
    df["Peaks"] = ""
    for i in r_peaks:
        df["Peaks"][i] = "R"
    peaks, _ = find_peaks(filtered_signal, height=-100)
    trough, _ = find_peaks(-filtered_signal, height=0)
    peaks = np.concatenate([peaks,trough],axis = 0)
    peaks = sorted(peaks)
    for i in range(0,len(peaks)):
        if  df["Peaks"][peaks[i]] == "R":
            df["Peaks"][peaks[i + 1]] = "S"
            df["Peaks"][peaks[i - 1]] = "Q"
    for i in range(0,len(peaks)):
        if df["Peaks"][peaks[i]] == "S":
            df["Peaks"][peaks[i + 1]] = "QRS_complex_off"
        if df["Peaks"][peaks[i]] == "Q":
            df["Peaks"][peaks[i - 1]] = "QRS_complex_on"
    peaks2, _ = find_peaks(filtered_signal, height=0)

    peaks3 = []
    for i in range(0,len(df)):
        if df["Peaks"][i] == "R":
            peaks3.append(i)
    peaks3 = np.array(peaks3)
    lag = np.array(0)
    fark = []
    lag = pd.Series(peaks3).shift(1)
    for i in range(1,len(lag)):
        if peaks3[i] - lag[i] > 10:
            fark.append(peaks3[i] - lag[i])
    tehlike = [] 
    for _ in range(0,peaks3[0]):
        tehlike.append(0)
    for i in range(1,len(peaks3)):
        if peaks3[i] - peaks3[i-1]> np.mean(fark) + 360 * 0.08:
            for _ in range(peaks3[i-1],peaks3[i]):
                tehlike.append(1)
        else:
            for _ in range(peaks3[i-1],peaks3[i]):
                tehlike.append(0)
    for _ in range(peaks3[-1],len(filtered_signal)):
        tehlike.append(0)
    df["AFIB_STATUS"] = tehlike
   
    x_degerleri = []
    y_degerleri = []
    for i in range(peaks3[0],peaks3[-1]):
        if (tehlike[i -1] == 0) & (tehlike[i] == 1):
            x_degerleri.append(i)
        if (tehlike[i -1] == 1) & (tehlike[i] == 0):
            y_degerleri.append(i)
    df["Aralık"] = ""
    for x,y in zip(x_degerleri,y_degerleri):
        for i in range(peaks3[0],peaks3[-1]):
            if (df.index[i] >= x-720) & (df.index[i] <= y+720):
                df["Aralık"][i] = (df["Saniye"][x].round(2),df["Saniye"][y].round(2))
                
    return df
                    
def make_plot1(df):
    data=ColumnDataSource(data={"x":df["Saniye"],"y":df["ECG"],"z":df["AFIB_STATUS"],
                                "r":df[df["Peaks"]=="R"],"q":df[df["Peaks"]=="Q"],
                               "s":df[df["Peaks"]=="S"],"p":df[df["Peaks"]=="QRS_complex_on"],
                               "t":df[df["Peaks"]=="QRS_complex_off"]})
    hover_tool1 = HoverTool(tooltips=[
    ("ECG Value","@y"),
    ("AFIB Status","@z"),
    ("Second","@x")
    ])
    plot1 = figure(tools=[hover_tool1],x_axis_label="Second",y_axis_label="ECG Value",
                   title = "Basic ECG Analysis",plot_width=1500, plot_height=500)
    plot1.xaxis.ticker = SingleIntervalTicker(interval=0.04)
    plot1.xgrid.grid_line_color="LightPink"
    plot1.yaxis.ticker = SingleIntervalTicker(interval=0.04)
    plot1.ygrid.grid_line_color="LightPink"
    
    plot1.line(x="x",y="y",source=data)
    for data,name,color in zip([data.data["r"],data.data["q"],data.data["s"],data.data["p"],
                            data.data["t"]],["R","Q","S","QRS_complex_on","QRS_complex_off"],
                           ["red","green","gray","cyan","black"]):
    #df = pd.DataFrame(data)
        plot1.circle(data["Saniye"],data["ECG"],color=color,alpha=0.8,
                     muted_color=color,muted_alpha=0.1,legend_label=name,size=8)
    plot1.legend.location="top_right"
    plot1.legend.click_policy = "mute"
    callback2 = CustomJS(args=dict(plot1=plot1), code="""
                    var a = cb_obj.value;
                    plot1.x_range.start = a[0];
                    plot1.x_range.end = a[1];
                    plot1.change.emit();
                    cb_obj.title = "Interval is " + a[0] + " Second to " + a[1] + " Second" 
                    """)
    slider_widget = RangeSlider(start=df["Saniye"].min(),end=df["Saniye"].max(),step = 1,
                                value=(df["Saniye"].min(),df["Saniye"].max()),
                                title="Select Second Interval")
    slider_widget.js_on_change("value_throttled",callback2)
    return plot1,slider_widget
def make_plot2(df):
    TOOLS = "tap"

    hover_tool = HoverTool(tooltips=[
                        ("Distance","@dist")
                        ])
    plot1 = figure(x_axis_label="Second",y_axis_label="ECG Value",
                   title = "Basic AFIB Analysis",plot_width=1500, plot_height=500,
                   tools=[TOOLS,hover_tool])
    plot1.xaxis.ticker = SingleIntervalTicker(interval=0.04)
    plot1.xgrid.grid_line_color="LightPink"
    plot1.yaxis.ticker = SingleIntervalTicker(interval=0.04)
    plot1.ygrid.grid_line_color="LightPink"
    data3 = ColumnDataSource(data={"true":df[df["AFIB_STATUS"] == 1],
                               "false":df[df["AFIB_STATUS"] == 0]})
    for data,name,color in zip([data3.data["true"],data3.data["false"]],["Yes","No"],
                               ["red","blue"]):
        plot1.line(data["Saniye"],data["ECG"],color=color,alpha=1,
                   muted_color=color,muted_alpha=0.1,legend_label=name)
    plot1.legend.location="top_left"
    plot1.legend.click_policy = "mute"
    data=ColumnDataSource(data={"r":df[df["Peaks"]=="R"],"q":df[df["Peaks"]=="Q"],
                               "s":df[df["Peaks"]=="S"],"p":df[df["Peaks"]=="QRS_complex_on"],
                               "t":df[df["Peaks"]=="QRS_complex_off"],
                               })
    for data,name,color in zip([data.data["r"],data.data["q"],data.data["s"],data.data["p"],
                            data.data["t"]],["R","Q","S","QRS_complex_on","QRS_complex_off"],
                           ["red","green","gray","cyan","black"]):
    #df = pd.DataFrame(data)
        plot1.circle(data["Saniye"],data["ECG"],color=color,alpha=0.8,
                     muted_color=color,muted_alpha=0.1,legend_label=name,size=4)
    plot1.legend.location="top_right"
    plot1.legend.click_policy = "mute"
    source = ColumnDataSource(data=dict(x=[], y=[],dist=[]))
    plot1.line(x="x",y="y",source=source) 
    plot1.circle(source=source,x='x',y='y',size=8) 
    callback2 = CustomJS(args=dict(plot1=plot1), code="""
                    var a = cb_obj.value;
                    plot1.x_range.start = a[0];
                    plot1.x_range.end = a[1];
                    plot1.change.emit();
                    cb_obj.title = "Interval is " + a[0] + " Second to " + a[1] + " Second" 
                    """)
    slider_widget = RangeSlider(start=df["Saniye"].min(),end=df["Saniye"].max(),step = 1,
                                value=(df["Saniye"].min(),df["Saniye"].max()),
                                title="Select Second Interval")
    slider_widget.js_on_change("value",callback2)
    callback = CustomJS(args=dict(source=source,plot1=plot1,slider_widget=slider_widget),code="""
    // the event that triggered the callback is cb_obj:
    // The event type determines the relevant attributes
    
        var data = source.data;
        var x = data['x']
        var y = data['y']
        var dist = data['dist']
        if(x.length < 1) {
                x.push(cb_obj.x)
                y.push(cb_obj.y)
                dist.push(cb_obj.x - 0)
                
                }
        else if(x.length == 1) {
                x.push(cb_obj.x)
                y.push(cb_obj.y)
                dist.push(cb_obj.x - x[0])

                
            } 
        else  {
                source.data["x"] = []
                source.data["y"] = []
                }
        
        
        source.change.emit();
    
    """)
    plot1.js_on_event('tap', callback)
    callback3 = CustomJS(args=dict(plot1=plot1,slider_widget=slider_widget), code="""
                    var a = slider_widget.value;
                    plot1.x_range.start = a[0];
                    plot1.x_range.end = a[1];
                    plot1.change.emit(); 
                    """)
                    
    
    plot1.js_on_event(MouseMove, callback3)
    return plot1,slider_widget


    



            
page = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
  {{ resources }}
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-giJF6kkoqNQ00vy+HMDP7azOuL0xtbfIcaT9wjKHr8RbDVddVHyTfAAsrekwKmP1" crossorigin="anonymous">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/js/bootstrap.bundle.min.js" integrity="sha384-ygbV9kiqUc6oa4msXn9868pTtWMgiQaeYH7/t7LECLbyPA2x65Kgf80OJFdroafW" crossorigin="anonymous"></script>

</head>
<body>
   <nav class="navbar navbar-light bg-light">
        <a class="navbar-brand" >
          <img src="/static/preloadedLogo.png" width="150" height="50" class="d-inline-block align-top" alt="">
          <ul class="nav nav-tabs">
            <li class="nav-item">
                <a class="nav-item nav-link" style="color: red;" href="/home">Go Home</a>
            </li>
        </a>
   </nav>
   <!--Our div is hidden by default-->
        <div id="message" style="display:none;">Loading takes a few seconds!</div>
        
        <script src="https://code.jquery.com/jquery-1.12.4.min.js"></script>
        <script>
        //When the page has loaded.
        $( document ).ready(function(){
            $('#message').fadeIn('slow', function(){
               $('#message').delay(4000).fadeOut(); 
            });
        });
        </script>
  <div id="myplot"></div>
  <script>
  fetch('/plot')
    .then(function(response) { return response.json(); })
    .then(function(item) { return Bokeh.embed.embed_item(item); })
  </script>
</body>
""")
@login_manager.user_loader 
def load_user(user_id):
    return Doctor.query.get(user_id)

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Doctor.query.filter_by(email=form.email.data).first()
        if user is not None:
            if user.check_password(form.password.data) & user.confirmed == True:
            
                login_user(user)
                flash('Logged in successfully.')
                next = request.args.get('next')
                if not is_safe_url(next):
                    return abort(400)
                return redirect(next or url_for('home'))
        #return redirect(url_for("home"))
    else:
        flash("Your account incorrect")
    

    return render_template('login.html', form=form)

    
@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.check_email(form.email):
            flash("Your email used")
        else:
            
            user = Doctor(title_name=form.title_name.data,
                          email=form.email.data,
                          password=form.password.data,
                          confirmed=False,
                          confirmed_on=None,
                          hospital_name=form.hospital_name.data)
            db.session.add(user)
            db.session.commit()   
            token = generate_confirmation_token(user.email)
            confirm_url = url_for("confirm_email",token=token,_external=True)
            html=render_template("activate.html", confirm_url=confirm_url)
            subject="Please confirm your email"
            send_email(user.email, subject, html)
            login_user(user)
            flash('A confirmation email has been sent via email.', 'success')
            return redirect(url_for("confirmemail"))
    return render_template("register.html", form=form)
@app.route("/confirm/<token>")
@login_required
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    user = Doctor.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.confirmed = True
        user.confirmed_on = datetime.datetime.now()
        db.session.add(user)
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for("home"))
@app.route("/confirmemail")
@login_required
def confirmemail():
    return render_template("confirm_mail.html")
@app.route("/home")
@login_required
def home():
    return render_template("home.html")

@app.route("/reset/<token>",methods=['GET', 'POST'])
def reset_password(token):
    form = PasswordResetForm()
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    user = Doctor.query.filter_by(email=email).first_or_404()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)

@app.route("/resetenteremail",methods=["GET","POST"])
def resetenteremail():
    form=ResetEmailForm()
    if form.validate_on_submit():
        if form.check_email(form.email):
            token = generate_confirmation_token(form.email.data)
            confirm_url = url_for("reset_password",token=token,_external=True)
            html=render_template("activate_reset.html", confirm_url=confirm_url)
            subject="Reset Password"
            send_email(form.email.data, subject, html)
            return redirect(url_for("resetemail"))
    return render_template("reset_emailform.html", form=form)


@app.route("/resetemail")
def resetemail():
    return render_template("reset_email.html")       
    
    
@app.route("/changehospital",methods=['GET', 'POST'])
@login_required
def changehospital():
    form=ChangeHospitalForm()
    email = current_user.email
    user = Doctor.query.filter_by(email=email).first()
    if form.validate_on_submit():
        user.hospital_name = form.hospital.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("home"))    
    return render_template("change_hospital.html",form=form )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/ecg/<patient>")
@login_required
def ecg_report(patient):
    session["patient"] = patient
    return redirect(url_for("root"))

    


    
@app.route('/report')
@login_required
def root():
    return page.render(resources=CDN.render())

@app.route('/plot')
def plot():
    patient = session.get("patient")
    user = Patient.query.filter_by(name=patient).first()
    a = ECGDB.query.with_entities(ECGDB.ecg_values).join(Patient).filter(ECGDB.patient_id == user.id).all()
    list_ecg = []
    for i in a:
        i_dict = i._asdict()
        list_ecg.append(i_dict["ecg_values"])
    df = ecg_processing(list_ecg)
    print(df["Peaks"].value_counts())
    plot1,slider_widget = make_plot1(df)
    plot2,slider_widget2 = make_plot2(df)
    
    df = df.replace({np.nan: None})
    select = Select(title="AFIB Places:(Only to inform)", value="value", options=[str(i) for i in df["Aralık"].unique() if i != "None"])

    layout = column(plot1,slider_widget,select,slider_widget2,plot2)
    return json.dumps(json_item(layout, "myplot"))
    

if __name__=="__main__":
    app.run(debug=True,use_reloader=False,port=5000)
#%%
user = Doctor.query.get(1)
print(user.title_name)
patient = Patient(name="Ayşe Serim",
                  email="fuatsezer1996@gmail.com",
                  password="saasasas",
                  confirmed=False,
                  confirmed_on=None)
patient.doctor_id = user.id
db.session.add(patient)
db.session.commit()
#%%
user = Doctor.query.get(1)
print(user.title_name)
patient = Patient(name="Fatma Kerim",
                  email="fuatse@gmail.com",
                  password="dsdfdfdf",
                  confirmed=False,
                  confirmed_on=None)
patient.doctor_id = user.id
db.session.add(patient)
db.session.commit()
#%%
print(user.patients.order_by(Patient.name.desc()).all())

#%%
df = pd.read_excel('ECG.xlsx')

ecg_value = df["ECG"]
#%%
user = Patient.query.get(1)
print(user.name)
for i in range(501,60000):
    print(i)
    ecg = ECGDB(ecg_values=ecg_value[i])
    ecg.patient_id = user.id
    db.session.add(ecg)
    db.session.commit()

#%%
a = ECGDB.query.with_entities(ECGDB.ecg_values).join(Patient).filter(ECGDB.patient_id == user.id).all()
list_ecg = []
for i in a:
    i_dict = i._asdict()
    list_ecg.append(i_dict["ecg_values"])

#%%
user = Patient.query.filter_by(name="Fatma Kerim").first()
a = ECGDB.query.with_entities(ECGDB.ecg_values).join(Patient).filter(ECGDB.patient_id == user.id).all()
list_ecg = [] 
for i in a:
    i_dict = i._asdict()
    list_ecg.append(i_dict["ecg_values"])
df = ecg_processing(list_ecg)
plot1 = make_plot1(df)
json= json.dumps(json_item(plot1, "myplot"))