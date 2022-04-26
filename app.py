import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash


# datetime object containing current date and time


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


# export API_KEY=pk_b9e1eb930e294dee8dd62fbccc11ac3c

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

    user_id = session["user_id"]

    stocks = db.execute(
        "SELECT name,time,price , SUM (shares) as TotalShares, symbol FROM transactions WHERE user_id == ? GROUP BY symbol ", user_id)

    usercash = db.execute("SELECT cash FROM users WHERE id == ?", user_id)[0]["cash"]

    totalcash = usercash

    for stock in stocks:
        totalcash += stock["price"]*stock["TotalShares"]

    """Show portfolio of stocks"""
    return render_template("index.html", stocks=stocks, usercash=usercash, totalcash=totalcash, usd=usd)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        symbol = request.form.get("symbol")

        result = lookup(symbol)

        if not symbol:
            return apology("must provide symbol")

        elif not result:
            return apology("This symbol does not exist")

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Shares must be ineger")

        if shares <= 0:
            return apology("Enter positive number")

        user_id = session["user_id"]

        usercash = db.execute("SELECT cash FROM users WHERE id == ?", user_id)[0]["cash"]

        item_name = result["name"]

        item_price = result["price"]

        total_price = item_price * shares

        # create usertable

        if usercash < total_price:
            return apology("Insufficent funds")

        else:
            new_cash = usercash - total_price
            db.execute("INSERT INTO transactions (user_id,name,shares,type,symbol, price) VALUES(?,?,?,?,?,?)",
                       user_id, item_name, shares, "buy", symbol, item_price)

            db.execute("UPDATE  users SET cash = ? WHERE id == ?", new_cash, user_id)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_id = session["user_id"]

    transactions = db.execute("SELECT symbol, price, time,type,shares FROM transactions WHERE user_id= ? ", user_id)

    return render_template("history.html", transactions=transactions, usd=usd)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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

    if request.method == "POST":

        symbol = request.form.get("symbol")

        if not symbol:
            return apology("must provide symbol")

        result = lookup(symbol)

        if result == None:
            return apology("This symbol does not exist")

        else:
            return render_template("quoted.html", result=result)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        conformation = request.form.get("confirmation")

        if not username:
            return apology("must provide username")

        elif not password:
            return apology("must provide password")

        elif not conformation:
            return apology("must conform password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) == 1:
            return apology("username already exists")

            # Ensure password was submitted

        elif password != conformation:
            return apology("passwords do not match")

        else:
            hash = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash ) VALUES (? ,?)", username, hash)

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":

        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Enter the symbol")

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Shares must be ineger")

        if shares <= 0:
            return apology("Enter positive number")

        result = lookup(symbol)

        if not result:
            return apology("Incorrect Symbol")

        item_name = result["name"]

        item_price = result["price"]

        shares_owned = db.execute("SELECT shares FROM  transactions WHERE user_id = ?  AND symbol = ?  GROUP BY symbol ", user_id, symbol)[
            0]["shares"]

        if shares_owned < shares:
            return apology("You don't have enougth shares")

        usercash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        new_cash = usercash + item_price * shares

        db.execute("UPDATE  users SET cash = ? WHERE id = ?", new_cash, user_id)

        db.execute("INSERT INTO transactions (user_id,name,shares,type,symbol, price) VALUES(?,?,?,?,?,?)",
                   user_id, item_name, -shares, "sell", symbol, item_price)

        return redirect("/")

    else:
        symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = ?  GROUP BY symbol", user_id)

        return render_template("sell.html",  symbols=symbols)
