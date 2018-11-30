import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, admin_login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///dunsterdash.db")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify(bool(db.execute("SELECT username FROM users WHERE username = :username", username=request.args.get("username"))))

@app.route("/menu")
@login_required
def menu():
    return render_template("menu.html")


@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/order")
@login_required
def order():
    if request.method == "POST":
        if not request.form.get("order"):
            return apology("You must input your order", 403)

        elif not request.form.get("deliverroom"):
            return apology("You must input the room you are in", 403)

        # Insert into database the user, order, and room number
        db.execute("INSERT INTO orders (username, food, deliverroom) VALUES (:username, :food, :deliverroom)",
                        username=username, food=request.form.get("order"), deliverroom=request.form.get("deliverroom"))

    return render_template("order.html")


@app.route("/orders")
@admin_login_required
def orders():

    # Select all transactions from the day

    return render_template("orders.html", placed_orders = orders)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # Get the username to sort transactions by
    username = db.execute("SELECT username from users WHERE id = :user_id", user_id=session["user_id"])[0]["username"]
    # Get all transactions from the user

    return render_template("history.html", previous_orders=orders)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    # Forget any user_id
    session.clear()

    """Register user"""
    username = request.form.get("username")
    password = request.form.get("password")

    if request.method == "POST":

        # Ensure the user typed in a username
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 400)

        # Ensure that the password matches the confirmation
        elif request.form.get("confirmation") != password:
            return apology("Your password must match the confirmation", 400)

        # Ensure that the password matches the confirmation
        elif not request.form.get("email"):
            return apology("You must provide an email", 400)

        # Ensure that the password matches the confirmation
        elif not request.form.get("house"):
            return apology("You must provide a house", 400)

        # Ensure that the password matches the confirmation
        elif not request.form.get("room"):
            return apology("You must provide a room", 400)

        usercheck = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        if usercheck:
            return apology("Username has already been taken", 400)

        else:

            # Hash the password
            hashed_pw = generate_password_hash(password)

            # Insert user into table of users
            db.execute("INSERT INTO users (username, hash, email, house, room, number) VALUES (:username, :hash, :email, :house, :room, :number)",
                        username=username, hash=hashed_pw, email=request.form.get("email"), house=request.form.get("house"),
                        room=request.form.get("room"), number=request.form.get("number"))

            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

    return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)