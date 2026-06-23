import sqlite3
import random
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'typespeed-secret-key-change-in-production'
DATABASE = 'database.db'


# ─────────────────────────── DB helpers ───────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS texts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content    TEXT NOT NULL,
            difficulty TEXT NOT NULL CHECK(difficulty IN ('easy','medium','hard')),
            language   TEXT DEFAULT 'ru',
            author     TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS results (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            text_id    INTEGER REFERENCES texts(id),
            wpm        INTEGER NOT NULL,
            accuracy   INTEGER NOT NULL,
            time_sec   REAL NOT NULL,
            difficulty TEXT NOT NULL,
            timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()

    # Seed texts if empty
    count = db.execute('SELECT COUNT(*) FROM texts').fetchone()[0]
    if count == 0:
        texts = [
            # easy
            ('Кот лежал на диване и грелся на солнышке. Было тихо и спокойно.', 'easy'),
            ('Шла Саша по шоссе и сосала сушку. Мимо ехала машина.', 'easy'),
            ('На дворе трава, на траве дрова. Не руби дрова на траве двора.', 'easy'),
            ('Летом дети ходят купаться на речку. Вода тёплая и прозрачная.', 'easy'),
            ('Мама мыла раму. Папа читал газету. Дети играли во дворе.', 'easy'),
            ('Съешь ещё этих мягких французских булок да выпей же чаю.', 'easy'),
            ('Белые облака плыли по голубому небу. Было тепло и солнечно.', 'easy'),
            ('Синица сидела на ветке и пела. Её песня была звонкой и весёлой.', 'easy'),
            # medium
            ('Требует душа поэта слагать стихи с утра, но муза, как назло, ушла гулять до вечера и вернуться не спешит.', 'medium'),
            ('Вчера я совершенно случайно обнаружил, что мой кот умеет открывать холодильник лапой и таскать оттуда колбасу.', 'medium'),
            ('Согласно последним данным, проект будет запущен в следующем квартале, если команда успеет исправить все критические ошибки.', 'medium'),
            ('Я люблю мрачную осень с её листопадом и холодным ветром, пробирающим до костей, когда хочется горячего чая.', 'medium'),
            ('Синхрофазотрон ускорил протоны до субсветовой скорости в ходе очередного эксперимента по физике элементарных частиц.', 'medium'),
            ('Революция требует отваги и самоотверженности от каждого, кто решился встать на путь перемен и борьбы за идеалы.', 'medium'),
            ('The quick brown fox jumps over the lazy dog near the riverbank at dusk.', 'medium'),
            ('She sells seashells by the seashore and the shells she sells are seashells for sure.', 'medium'),
            # hard
            ('Трансцендентальная эстетика Канта определяет априорные формы чувственности — пространство и время — как условия возможности опыта вообще.', 'hard'),
            ('Экзистенциальная дилемма квази-унитарной матрицы не имеет тривиального решения в пространстве действительных чисел конечной размерности.', 'hard'),
            ('Сверхзвуковой истребитель-перехватчик промчался в стратосфере, оставив за собой инверсионный след, растворившийся в морозном воздухе.', 'hard'),
            ('How much wood would a woodchuck chuck if a woodchuck could chuck wood? A woodchuck would chuck all the wood.', 'hard'),
            ('Pack my box with five dozen liquor jugs and do not forget to label every single one of them carefully.', 'hard'),
            ('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.', 'hard'),
            ('Флюорографическое исследование выявило микроскопические изменения в паренхиме лёгких, требующие дополнительной дифференциальной диагностики специалиста.', 'hard'),
            ('Постструктуралистский дискурс деконструирует логоцентризм западной метафизики, обнажая апории языка в точках предельного смыслопорождения.', 'hard'),
        ]
        db.executemany('INSERT INTO texts (content, difficulty) VALUES (?, ?)', texts)
        db.commit()
    db.close()


# ─────────────────────────── Auth helpers ────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    db.close()
    return user


# ─────────────────────────── Routes: Auth ────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        if not username or not email or not password:
            flash('Заполните все поля', 'error')
            return redirect(url_for('register'))
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username=? OR email=?', (username, email)).fetchone()
        if existing:
            flash('Пользователь с таким именем или email уже существует', 'error')
            db.close()
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        db.execute('INSERT INTO users (username, email, password) VALUES (?,?,?)', (username, email, hashed))
        db.commit()
        user = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        db.close()
        session['user_id'] = user['id']
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─────────────────────────── Routes: Main ────────────────────────

@app.route('/')
@login_required
def index():
    user = current_user()
    db = get_db()
    stats = db.execute('''
        SELECT COUNT(*) as total, MAX(wpm) as best_wpm,
               ROUND(AVG(wpm)) as avg_wpm, ROUND(AVG(accuracy)) as avg_acc
        FROM results WHERE user_id=?
    ''', (user['id'],)).fetchone()
    db.close()
    return render_template('index.html', user=user, stats=stats)


@app.route('/start_test')
@login_required
def start_test():
    level = request.args.get('level', 'easy')
    db = get_db()
    rows = db.execute('SELECT * FROM texts WHERE difficulty=?', (level,)).fetchall()
    db.close()
    if not rows:
        return jsonify({'error': 'No texts'}), 404
    chosen = random.choice(rows)
    return jsonify({'text': chosen['content'], 'text_id': chosen['id']})


@app.route('/submit_result', methods=['POST'])
@login_required
def submit_result():
    data = request.json
    user_id = session['user_id']
    db = get_db()
    db.execute('''
        INSERT INTO results (user_id, text_id, wpm, accuracy, time_sec, difficulty)
        VALUES (?,?,?,?,?,?)
    ''', (user_id, data.get('text_id'), data['wpm'], data['accuracy'],
          float(data['time']), data.get('difficulty', 'easy')))
    db.commit()
    db.close()
    return jsonify({'status': 'ok'})


# ─────────────────────────── Routes: Profile ─────────────────────

@app.route('/profile')
@login_required
def profile():
    user = current_user()
    db = get_db()
    stats = db.execute('''
        SELECT COUNT(*) as total,
               MAX(wpm) as best_wpm,
               ROUND(AVG(wpm)) as avg_wpm,
               ROUND(AVG(accuracy),1) as avg_acc,
               ROUND(SUM(time_sec)/60, 1) as total_min
        FROM results WHERE user_id=?
    ''', (user['id'],)).fetchone()

    by_level = db.execute('''
        SELECT difficulty, COUNT(*) as cnt, MAX(wpm) as best, ROUND(AVG(wpm)) as avg_wpm
        FROM results WHERE user_id=?
        GROUP BY difficulty ORDER BY CASE difficulty WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 WHEN 'hard' THEN 3 END
    ''', (user['id'],)).fetchall()

    history = db.execute('''
        SELECT r.wpm, r.accuracy, r.time_sec, r.difficulty, r.timestamp,
               t.content as text
        FROM results r LEFT JOIN texts t ON r.text_id=t.id
        WHERE r.user_id=?
        ORDER BY r.timestamp DESC LIMIT 20
    ''', (user['id'],)).fetchall()

    # chart data — last 20 wpm
    chart_data = db.execute('''
        SELECT wpm, timestamp FROM results WHERE user_id=?
        ORDER BY timestamp DESC LIMIT 20
    ''', (user['id'],)).fetchall()
    chart_wpm = [r['wpm'] for r in reversed(chart_data)]
    chart_labels = [r['timestamp'][11:16] for r in reversed(chart_data)]

    db.close()
    return render_template('profile.html', user=user, stats=stats,
                           by_level=by_level, history=history,
                           chart_wpm=chart_wpm, chart_labels=chart_labels)


# ─────────────────────────── Routes: Leaderboard ─────────────────

@app.route('/leaderboard')
@login_required
def leaderboard():
    user = current_user()
    db = get_db()

    top_all = db.execute('''
        SELECT u.username, r.wpm, r.accuracy, r.difficulty, r.timestamp
        FROM results r JOIN users u ON r.user_id=u.id
        ORDER BY r.wpm DESC LIMIT 10
    ''').fetchall()

    top_easy = db.execute('''
        SELECT u.username, MAX(r.wpm) as wpm, r.accuracy
        FROM results r JOIN users u ON r.user_id=u.id
        WHERE r.difficulty='easy' GROUP BY r.user_id ORDER BY wpm DESC LIMIT 10
    ''').fetchall()

    top_medium = db.execute('''
        SELECT u.username, MAX(r.wpm) as wpm, r.accuracy
        FROM results r JOIN users u ON r.user_id=u.id
        WHERE r.difficulty='medium' GROUP BY r.user_id ORDER BY wpm DESC LIMIT 10
    ''').fetchall()

    top_hard = db.execute('''
        SELECT u.username, MAX(r.wpm) as wpm, r.accuracy
        FROM results r JOIN users u ON r.user_id=u.id
        WHERE r.difficulty='hard' GROUP BY r.user_id ORDER BY wpm DESC LIMIT 10
    ''').fetchall()

    # user rank
    rank = db.execute('''
        SELECT COUNT(*)+1 as rank FROM (
            SELECT user_id, MAX(wpm) as best FROM results GROUP BY user_id
        ) WHERE best > (SELECT COALESCE(MAX(wpm),0) FROM results WHERE user_id=?)
    ''', (user['id'],)).fetchone()

    db.close()
    return render_template('leaderboard.html', user=user,
                           top_all=top_all, top_easy=top_easy,
                           top_medium=top_medium, top_hard=top_hard,
                           rank=rank)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
