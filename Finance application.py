import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get Cash the user has left and the symbols of the stocks they own
    cash = db.execute("SELECT cash from users WHERE id = :user_id", user_id=session["user_id"])[0]["cash"]
    username = db.execute("SELECT username from users WHERE id = :id", id=session["user_id"])[0]["username"]
    transactions = db.execute("SELECT * from history WHERE user = :id;", id=username)

    # Create dict for stocks
    owned = {}

    # Iterate over all the transactions
    for indvstock in transactions:
        # Use lookup function to get name and price per share
        symbols = lookup(indvstock["symbol"])
        name = symbols["name"]
        price = symbols["price"]
        symbol = symbols["symbol"]

        # Calculate the number of shares for each stock that the user has
        if owned.get(symbol):
            owned[symbol]["shares"] += indvstock["shares"]
        else:
            # Input variables into dict.
            owned[symbol] = {"shares": indvstock["shares"], "price": price, "name": name}

        # Find the total price of all of the shares that the user has
        owned[symbol]["total"] = owned[symbol]["shares"] * price

    return render_template("index.html", owned=owned, cash=cash, total=sum([x[1]["total"] for x in owned.items()])+cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide a stock symbol", 400)

        # Lookup symbol
        check = lookup(request.form.get("symbol"))

        # Check if the symbol is valid
        if not check:
            return apology("must provide valid stock symbol", 400)

        # Create an integer for shares
        shares = int(request.form.get("shares"))

        # Check if integer for shares is positive
        if shares <= 0:
            return apology("number of shares must be a positive integer")

        # Check how much cash the user has
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])

        # Check if the user has enough cash to make the purchase
        if not cash or float(cash[0]["cash"]) < (check["price"] * shares):
            return apology("Insufficient funds")

        # Update transaction history and cash. Table inserts current timestamp with each entry
        else:
            username = db.execute("SELECT username FROM users WHERE id = :id", id=session["user_id"])[0]["username"]

            db.execute("INSERT INTO history (symbol, shares, price, user) VALUES (:symbol, :shares, :price, :user)",
                       symbol=check["symbol"], shares=shares, price=check["price"], user=username)

            db.execute("UPDATE users SET cash = cash - :spent WHERE id = :id",
                       spent=(check["price"] * float(shares)), id=session["user_id"])

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    username = db.execute("SELECT username FROM users WHERE id = :id", id=session["user_id"])[0]["username"]
    transactions = db.execute("SELECT * FROM history WHERE user = :username ORDER BY time;", username=username)
    return render_template("history.html", transactions=transactions)


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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide a stock symbol", 400)

        # Lookup symbol
        else:
            quote = lookup(request.form.get("symbol"))

        # Check if symbol exists
        if not quote:
            return apology("must provide valid stock symbol", 400)

        # If the symbol exists, print its name and value
        else:
            return render_template("quoted.html", name=quote["name"], symbol=quote["symbol"], price=quote["price"])

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure new password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirm password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure confirm passowrd matches
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("ensure password fields match", 400)

        # Check if username has been taken
        usercheck = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        if usercheck:
            return apology("username already taken", 400)

        # Insert login info into database
        else:
            db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                       username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide a stock symbol", 400)

        # Lookup symbol
        else:
            stock = lookup(request.form.get("symbol"))

        # Check if symbol exists
        if not stock:
            return apology("must provide valid stock symbol", 400)

        # Create an integer for shares
        sellshares = int(request.form.get("shares"))

        # Check if integer for shares is positive
        if sellshares <= 0:
            return apology("number of shares must be a positive integer")

        # Check number of shares of specified stock owned by the user
        username = db.execute("SELECT username FROM users WHERE id = :id", id=session["user_id"])[0]["username"]

        transactions = db.execute("SELECT * from history WHERE user = :id;", id=username)

        # Iterate over all the transactions to find total shares of stock
        ownedshares = 0
        for indvstock in transactions:
            if indvstock["symbol"] == request.form.get("symbol"):
                indvstock["shares"] += ownedshares

        # Check if enough shares owned
        if not ownedshares < sellshares:
            return apology("you do not own enough shares of the given stock")

        # Record sale in history
        db.execute("INSERT INTO history (user, symbol, shares, price) VALUES(:user, :symbol, :shares, :price)",
                   user=username, symbol=stock["symbol"], shares=(-sellshares), price=(stock["price"]))

        # Increase user cash by sale amount
        db.execute("UPDATE users SET cash = cash + :sale WHERE id = :id",
                   id=session["user_id"], sale=(stock["price"] * float(sellshares)))

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("sell.html")


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add money to account"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("card"):
            return apology("must provide valid card number", 400)

        # Create an integer for shares
        addcash = int(request.form.get("cash"))

        # Check if integer for shares is positive
        if not addcash or addcash <= 0:
            return apology("must add positive integer cash value")

        # Add cash to user
        db.execute("UPDATE users SET cash = cash + :addcash WHERE id = :id", id=session["user_id"], addcash=addcash)

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("add.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)