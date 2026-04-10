import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# ── Database Connection ──
def get_db():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD'),
        dbname=os.environ.get('DB_NAME', 'postgres')
    )

# ── Home Page ──
@app.route('/')
def index():
    return render_template('index.html')

# ── Search Books ──
@app.route('/search')
def search_books():
    query = request.args.get('q', '')
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if query:
        cursor.execute(
            """SELECT b.bookid, b.title, b.sku, b.genre,
                      a."FirstName" || ' ' || a."LastName" AS authorname,
                      b.availablecopies
               FROM book b
               JOIN "Author" a ON b.authorid = a."AuthorID"
               WHERE b.title ILIKE %s
                  OR a."FirstName" ILIKE %s
                  OR a."LastName" ILIKE %s
               ORDER BY b.title""",
            (f'%{query}%', f'%{query}%', f'%{query}%')
        )
    else:
        cursor.execute(
            """SELECT b.bookid, b.title, b.sku, b.genre,
                      a."FirstName" || ' ' || a."LastName" AS authorname,
                      b.availablecopies
               FROM book b
               JOIN "Author" a ON b.authorid = a."AuthorID"
               ORDER BY b.title"""
        )

    books = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('search.html', books=books, query=query)

# ── Checkout a Book ──
@app.route('/checkout', methods=['POST'])
def checkout_book():
    book_id = request.form['book_id']
    member_id = request.form['member_id']
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO transactions (memberid, bookid) VALUES (%s, %s)",
            (member_id, book_id)
        )
        cursor.execute(
            "UPDATE book SET availablecopies = availablecopies - 1 WHERE bookid = %s AND availablecopies > 0",
            (book_id,)
        )
        db.commit()
        flash('Book checked out successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        db.close()
    return redirect(url_for('search_books'))

# ── Return a Book ──
@app.route('/return', methods=['POST'])
def return_book():
    transaction_id = request.form['transaction_id']
    book_id = request.form['book_id']
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE transactions SET returndate = CURRENT_DATE WHERE transactionid = %s",
            (transaction_id,)
        )
        cursor.execute(
            "UPDATE book SET availablecopies = availablecopies + 1 WHERE bookid = %s",
            (book_id,)
        )
        db.commit()
        flash('Book returned successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        db.close()
    return redirect(url_for('active_loans'))

# ── View Active Loans ──
@app.route('/loans')
def active_loans():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        """SELECT t.transactionid,
                  m."FullName" AS membername,
                  b.title, b.bookid, t.transactiondate, t.returndate
           FROM transactions t
           JOIN "Member" m ON t.memberid = m."MemberID"
           JOIN book b     ON t.bookid   = b.bookid
           ORDER BY t.returndate IS NULL DESC, t.transactiondate DESC"""
    )
    loans = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('loans.html', loans=loans)

# ── View Members ──
@app.route('/members')
def members():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        """SELECT "MemberID" AS memberid, "FullName" AS fullname,
                  "Email" AS email, "PhoneNumber" AS phonenumber,
                  "JoinDate" AS joindate, "MembershipType" AS membershiptype
           FROM "Member"
           ORDER BY "FullName" """
    )
    members = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('members.html', members=members)

if __name__ == '__main__':
    app.run(debug=True)