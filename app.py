# ============================================================
# ỨNG DỤNG QUẢN LÝ TÀI CHÍNH CÁ NHÂN - Finance Manager
# ============================================================
# CÁC THƯ VIỆN CẦN CÀI ĐẶT:
# pip install streamlit pandas plotly openpyxl
# ============================================================

import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import re
import os
import json
from io import BytesIO

# ============================================================
# MÀU CHUẨN THEO ẢNH 2 - ĐÃ SỬA
# ============================================================
COLOR_THU_MAIN = "#00B42A"
COLOR_CHI_MAIN = "#F53F3F"
COLOR_DU = "#1565C0"

COLOR_THU = COLOR_THU_MAIN
COLOR_CHI = COLOR_CHI_MAIN
COLOR_THU_FILL = "rgba(0, 180, 42, 0.15)"
COLOR_CHI_FILL = "rgba(245, 63, 63, 0.15)"

COLORS_CHI = {
    "Nhà cửa": "#4285F4",
    "Ăn uống": "#EA4335",
    "Mua sắm": "#FBBC05",
    "Đi lại": "#9C27B0",
    "Di chuyển": "#9C27B0",
    "Giải trí": "#FF9800",
    "Khác": "#607D8B",
    "Hoá đơn": "#00ACC1",
    "Hóa đơn": "#00ACC1",
    "Sức khỏe": "#E91E63",
    "Giáo dục": "#3F51B5",
    "Quà tặng": "#FF5722",
}

COLORS_THU = {
    "Lương": "#0F9D58",
    "Bán đồ": "#673AB7",
    "Đầu tư": "#039BE5",
    "Đầu tư tài chính": "#039BE5",
    "Khác": "#FF9800",
    "Thưởng": "#8BC34A",
    "Quà tặng": "#4CAF50",
}

DEFAULT_COLOR_PALETTE = [
    "#4285F4", "#EA4335", "#FBBC05", "#9C27B0", "#FF9800", "#607D8B",
    "#00ACC1", "#E91E63", "#3F51B5", "#FF5722", "#8BC34A", "#009688",
    "#795548", "#FFC107", "#03A9F4", "#F44336"
]

def get_category_colors(categories, color_map, fallback_palette=None):
    if fallback_palette is None:
        fallback_palette = DEFAULT_COLOR_PALETTE
    used = set()
    result = []
    for cat in categories:
        if cat in color_map:
            result.append(color_map[cat])
            used.add(color_map[cat])
        else:
            result.append(None)
    pi = 0
    for i, c in enumerate(result):
        if c is None:
            while pi < len(fallback_palette) * 3 and fallback_palette[pi % len(fallback_palette)] in used:
                pi += 1
            result[i] = fallback_palette[pi % len(fallback_palette)]
            used.add(result[i])
            pi += 1
    return result

def colored_metric(label, value, color="#4d7c0f"):
    st.markdown(f"""
    <div style='background:white; padding:1.25rem 1.5rem; border-radius:1rem; 
                box-shadow:0 4px 12px rgba(77,124,15,0.08); border:1px solid #ecfccb;
                transition: transform 0.3s, box-shadow 0.3s;'>
        <div style='font-size:0.9rem; color:#78716c; font-weight:500; margin-bottom:0.5rem;'>{label}</div>
        <div style='font-size:1.75rem; font-weight:700; color:{color};'>{value}</div>
    </div>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="Quản Lý Tài Chính Cá Nhân",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Vietnamese_Vietnam.1252')
    except:
        pass

DB_PATH = "finance.db"

DEFAULT_CATEGORIES = {
    'expense': [
        ('Ăn uống', '🍜'), ('Di chuyển', '🚗'), ('Mua sắm', '🛒'),
        ('Hoá đơn', '📄'), ('Giải trí', '🎮'), ('Sức khỏe', '💊'),
        ('Giáo dục', '📚'), ('Nhà cửa', '🏠'), ('Quà tặng', '🎁'), ('Khác', '📦')
    ],
    'income': [
        ('Lương', '💼'), ('Thưởng', '🎉'), ('Đầu tư', '📈'),
        ('Bán đồ', '🛍️'), ('Quà tặng', '🎁'), ('Khác', '📦')
    ]
}

INVESTMENT_TYPES = [
    'Cổ phiếu', 'Trái phiếu', 'Quỹ đầu tư', 'Bất động sản',
    'Vàng', 'Tiền điện tử', 'Tiết kiệm ngân hàng', 'Khác'
]

def format_vnd(amount):
    try:
        amount = float(amount)
        return "{:,.0f}".format(amount).replace(",", ".") + " đ"
    except:
        return "0 đ"

def format_number_display(number):
    try:
        number = int(float(number))
        return f"{number:,}".replace(',', '.')
    except:
        return ""

def parse_money_input(text):
    if not text or not str(text).strip():
        return 0
    cleaned = str(text).replace('.', '').replace(' ', '').replace(',', '')
    try:
        return int(float(cleaned))
    except:
        return 0

def money_input(label, min_value=0, step=1000, value=None, key=None, help=None):
    if key is None:
        key = f"money_{label.replace(' ', '_').lower()}"
    min_value = int(min_value)
    step = int(step)
    input_params = {
        "label": f"{label}",
        "min_value": min_value,
        "step": step,
        "key": key,
        "help": help,
        "format": "%d"
    }
    if value is not None:
        try:
            val_int = int(float(value))
            if val_int > 0:
                input_params["value"] = val_int
        except (ValueError, TypeError):
            pass
    amount = st.number_input(**input_params)
    if amount and amount > 0:
        st.markdown(
            f"<div style='background: linear-gradient(90deg, #ecfdf5, #d1fae5); "
            f"padding: 0.6rem 1rem; border-radius: 0.5rem; margin-top: 0.25rem; "
            f"border-left: 4px solid {COLOR_THU}; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>"
            f"<span style='color: #065f46; font-size: 1.3rem; font-weight: bold;'>"
            f"💵 {format_vnd(int(amount))}</span></div>",
            unsafe_allow_html=True
        )
    return int(amount) if amount else 0

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

TOKEN_FILE = ".login_token"

def save_login_token(user_id, remember_days=30):
    token_data = {
        'user_id': user_id,
        'expires_at': (datetime.now() + timedelta(days=remember_days)).strftime('%Y-%m-%d %H:%M:%S')
    }
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(token_data, f)
        return True
    except:
        return False

def load_login_token():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            return token_data
    except:
        pass
    return None

def delete_login_token():
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return True
    except:
        return False

def check_login_token():
    token_data = load_login_token()
    if not token_data:
        return None
    try:
        expires_at = datetime.strptime(token_data['expires_at'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < expires_at:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (token_data['user_id'],))
            user = c.fetchone()
            conn.close()
            if user:
                return dict(user)
    except:
        pass
    delete_login_token()
    return None

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            icon TEXT DEFAULT '📦',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            deadline TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS savings_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_id INTEGER,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (goal_id) REFERENCES savings_goals(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            principal_amount REAL NOT NULL,
            current_value REAL NOT NULL,
            invest_date TEXT NOT NULL,
            expected_return REAL DEFAULT 0,
            status TEXT DEFAULT 'holding',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS investment_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investment_id INTEGER NOT NULL,
            value REAL NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (investment_id) REFERENCES investments(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL,
            due_date TEXT NOT NULL,
            recurring TEXT DEFAULT 'none',
            note TEXT,
            is_paid INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        conn.commit()
    except Exception as e:
        st.error(f"Lỗi khởi tạo database: {str(e)}")
    finally:
        conn.close()

def init_user_categories(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM categories WHERE user_id = ?", (user_id,))
        count = c.fetchone()[0]
        if count == 0:
            for cat_type, categories in DEFAULT_CATEGORIES.items():
                for name, icon in categories:
                    c.execute(
                        "INSERT INTO categories (user_id, name, type, icon) VALUES (?, ?, ?, ?)",
                        (user_id, name, cat_type, icon)
                    )
            conn.commit()
    except Exception as e:
        st.error(f"Lỗi khởi tạo danh mục: {str(e)}")
    finally:
        conn.close()

def register_user(full_name, email, password):
    if not is_valid_email(email):
        return False, "Email không hợp lệ!"
    if len(password) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự!"
    if not full_name.strip():
        return False, "Họ tên không được để trống!"
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        if c.fetchone():
            return False, "Email đã tồn tại!"
        password_hash = hash_password(password)
        c.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name.strip(), email.lower(), password_hash)
        )
        conn.commit()
        c.execute("SELECT id FROM users WHERE email = ?", (email.lower(),))
        user_id = c.fetchone()[0]
        init_user_categories(user_id)
        return True, "Đăng ký thành công! Vui lòng đăng nhập."
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def login_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        user = c.fetchone()
        if not user:
            return None, "Email không tồn tại!"
        if user['password_hash'] != hash_password(password):
            return None, "Mật khẩu không đúng!"
        return dict(user), "Đăng nhập thành công!"
    except Exception as e:
        return None, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def get_user_categories(user_id, cat_type=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        if cat_type:
            c.execute("SELECT * FROM categories WHERE user_id = ? AND type = ? ORDER BY name", (user_id, cat_type))
        else:
            c.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY type, name", (user_id,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        st.error(f"Lỗi lấy danh mục: {str(e)}")
        return []
    finally:
        conn.close()

def add_category(user_id, name, cat_type, icon='📦'):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categories (user_id, name, type, icon) VALUES (?, ?, ?, ?)",
                  (user_id, name.strip(), cat_type, icon))
        conn.commit()
        return True, "Thêm danh mục thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def delete_category(category_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def add_transaction(user_id, trans_type, amount, category, date, note):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO transactions (user_id, type, amount, category, date, note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, trans_type, amount, category, date, note)
        )
        conn.commit()
        return True, "Thêm giao dịch thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def get_transactions(user_id, limit=None, trans_type=None, category=None, start_date=None, end_date=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = [user_id]
        if trans_type:
            query += " AND type = ?"
            params.append(trans_type)
        if category:
            query += " AND category = ?"
            params.append(category)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        query += " ORDER BY date DESC, created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        c.execute(query, params)
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        st.error(f"Lỗi lấy giao dịch: {str(e)}")
        return []
    finally:
        conn.close()

def update_transaction(trans_id, user_id, trans_type, amount, category, date, note):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """UPDATE transactions SET type=?, amount=?, category=?, date=?, note=?
               WHERE id=? AND user_id=?""",
            (trans_type, amount, category, date, note, trans_id, user_id)
        )
        conn.commit()
        return True, "Cập nhật thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def delete_transaction(trans_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (trans_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_monthly_summary(user_id, year, month):
    conn = get_connection()
    c = conn.cursor()
    try:
        date_start = f"{year}-{month:02d}-01"
        if month == 12:
            date_end = f"{year+1}-01-01"
        else:
            date_end = f"{year}-{month+1:02d}-01"
        c.execute(
            """SELECT type, SUM(amount) as total FROM transactions
               WHERE user_id=? AND date >= ? AND date < ?
               GROUP BY type""",
            (user_id, date_start, date_end)
        )
        results = c.fetchall()
        summary = {'income': 0, 'expense': 0}
        for row in results:
            summary[row['type']] = row['total']
        return summary
    except Exception as e:
        return {'income': 0, 'expense': 0}
    finally:
        conn.close()

def add_savings_goal(user_id, name, target_amount, deadline, description):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO savings_goals (user_id, name, target_amount, deadline, description)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, name.strip(), target_amount, deadline, description)
        )
        conn.commit()
        return True, "Tạo mục tiêu thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def get_savings_goals(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM savings_goals WHERE user_id=? ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        return []
    finally:
        conn.close()

def update_savings_goal(goal_id, user_id, amount, trans_type, note):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM savings_goals WHERE id=? AND user_id=?", (goal_id, user_id))
        goal = c.fetchone()
        if not goal:
            return False, "Mục tiêu không tồn tại!"
        current = goal['current_amount']
        if trans_type == 'deposit':
            new_amount = current + amount
        else:
            if amount > current:
                return False, "Số tiền rút vượt quá số dư!"
            new_amount = current - amount
        c.execute("UPDATE savings_goals SET current_amount=? WHERE id=?", (new_amount, goal_id))
        c.execute(
            """INSERT INTO savings_transactions (user_id, goal_id, type, amount, date, note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, goal_id, trans_type, amount, datetime.now().strftime('%Y-%m-%d'), note)
        )
        conn.commit()
        return True, "Cập nhật thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def delete_savings_goal(goal_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM savings_transactions WHERE goal_id=? AND user_id=?", (goal_id, user_id))
        c.execute("DELETE FROM savings_goals WHERE id=? AND user_id=?", (goal_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_savings_transactions(user_id, goal_id=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        if goal_id:
            c.execute(
                """SELECT st.*, sg.name as goal_name FROM savings_transactions st
                   LEFT JOIN savings_goals sg ON st.goal_id = sg.id
                   WHERE st.user_id=? AND st.goal_id=? ORDER BY st.date DESC""",
                (user_id, goal_id)
            )
        else:
            c.execute(
                """SELECT st.*, sg.name as goal_name FROM savings_transactions st
                   LEFT JOIN savings_goals sg ON st.goal_id = sg.id
                   WHERE st.user_id=? ORDER BY st.date DESC""",
                (user_id,)
            )
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        return []
    finally:
        conn.close()

def add_investment(user_id, inv_type, name, principal, current_value, invest_date, expected_return):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO investments 
               (user_id, type, name, principal_amount, current_value, invest_date, expected_return)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, inv_type, name.strip(), principal, current_value, invest_date, expected_return)
        )
        inv_id = c.lastrowid
        c.execute(
            """INSERT INTO investment_updates (investment_id, value, date, note)
               VALUES (?, ?, ?, ?)""",
            (inv_id, current_value, invest_date, "Giá trị ban đầu")
        )
        conn.commit()
        return True, "Thêm khoản đầu tư thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def get_investments(user_id, status=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        if status:
            c.execute("SELECT * FROM investments WHERE user_id=? AND status=? ORDER BY created_at DESC", (user_id, status))
        else:
            c.execute("SELECT * FROM investments WHERE user_id=? ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        return []
    finally:
        conn.close()

def update_investment_value(inv_id, user_id, new_value, note):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE investments SET current_value=? WHERE id=? AND user_id=?", (new_value, inv_id, user_id))
        c.execute(
            """INSERT INTO investment_updates (investment_id, value, date, note)
               VALUES (?, ?, ?, ?)""",
            (inv_id, new_value, datetime.now().strftime('%Y-%m-%d'), note)
        )
        conn.commit()
        return True, "Cập nhật giá trị thành công!"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"
    finally:
        conn.close()

def sell_investment(inv_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE investments SET status='sold' WHERE id=? AND user_id=?", (inv_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def delete_investment(inv_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM investment_updates WHERE investment_id IN (SELECT id FROM investments WHERE id=? AND user_id=?)", (inv_id, user_id))
        c.execute("DELETE FROM investments WHERE id=? AND user_id=?", (inv_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_investment_updates(inv_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM investment_updates WHERE investment_id=? ORDER BY date", (inv_id,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        return []
    finally:
        conn.close()

def set_budget(user_id, category, amount, month):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM budgets WHERE user_id=? AND category=? AND month=?",
                  (user_id, category, month))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE budgets SET amount=? WHERE id=?", (amount, existing['id']))
        else:
            c.execute("INSERT INTO budgets (user_id, category, amount, month) VALUES (?, ?, ?, ?)",
                      (user_id, category, amount, month))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_budgets(user_id, month):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM budgets WHERE user_id=? AND month=?", (user_id, month))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        return []
    finally:
        conn.close()

def add_reminder(user_id, title, amount, due_date, recurring, note):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO reminders (user_id, title, amount, due_date, recurring, note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, title.strip(), amount, due_date, recurring, note)
        )
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_reminders(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM reminders WHERE user_id=? ORDER BY due_date", (user_id,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        return []
    finally:
        conn.close()

def mark_reminder_paid(reminder_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE reminders SET is_paid=1 WHERE id=? AND user_id=?", (reminder_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def delete_reminder(reminder_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (reminder_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def calculate_cagr(principal, current_value, years):
    if years <= 0 or principal <= 0:
        return 0
    return ((current_value / principal) ** (1 / years) - 1) * 100

def calculate_compound_interest(principal, rate, years, monthly_contribution=0):
    rate_monthly = rate / 100 / 12
    months = years * 12
    total = principal * (1 + rate_monthly) ** months
    if monthly_contribution > 0:
        total += monthly_contribution * (((1 + rate_monthly) ** months - 1) / rate_monthly)
    return total

def calculate_simple_interest(principal, rate, years):
    return principal * (1 + (rate / 100) * years)

def show_auth_page():
    st.markdown("""
        <style>
        .auth-container { max-width: 450px; margin: 0 auto; padding: 2rem; }
        .auth-title { text-align: center; color: #1E3A8A; font-size: 2rem; font-weight: bold; margin-bottom: 0.5rem; }
        .auth-subtitle { text-align: center; color: #6B7280; margin-bottom: 2rem; }
        </style>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">💰 Finance Manager</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Quản lý tài chính cá nhân thông minh</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
        with tab1:
            email_login = st.text_input("📧 Email", key="login_email")
            password_login = st.text_input("🔒 Mật khẩu", type="password", key="login_password")
            remember_me = st.checkbox("🔒 Ghi nhớ đăng nhập 30 ngày", key="remember_me")
            if st.button("Đăng nhập", use_container_width=True, type="primary"):
                user, msg = login_user(email_login, password_login)
                if user:
                    st.session_state['user'] = user
                    if remember_me:
                        save_login_token(user['id'], remember_days=30)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        with tab2:
            full_name = st.text_input("👤 Họ tên", key="reg_name")
            email_reg = st.text_input("📧 Email", key="reg_email")
            password_reg = st.text_input("🔒 Mật khẩu", type="password", key="reg_password")
            confirm_password = st.text_input("🔒 Xác nhận mật khẩu", type="password", key="reg_confirm")
            if st.button("Đăng ký", use_container_width=True, type="primary"):
                if password_reg != confirm_password:
                    st.error("Mật khẩu xác nhận không khớp!")
                else:
                    success, msg = register_user(full_name, email_reg, password_reg)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

def show_dashboard():
    if st.button("📋 Xem tất cả giao dịch", type="primary", key="btn_view_all_trans"):
        st.session_state["main_menu"] = "💰 Giao dịch hàng ngày"
        st.rerun()
        return

    user_id = st.session_state['user']['id']
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    summary = get_monthly_summary(user_id, current_year, current_month)
    total_income = summary['income']
    total_expense = summary['expense']
    balance = total_income - total_expense
    savings_rate = (balance / total_income * 100) if total_income > 0 else 0

    st.markdown("""
        <div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem;'>
            <div style='width: 60px; height: 60px; border-radius: 16px; 
                background: linear-gradient(135deg, #1E3A8A, #3b82f6); 
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 4px 15px rgba(30, 58, 138, 0.3);'>
                <span style='font-size: 28px;'>🏠</span>
            </div>
            <div>
                <h1 style='margin: 0; border: none; padding: 0;'>Tổng quan tài chính</h1>
                <p style='color: #64748b; margin: 0.25rem 0 0 0;'>
                    📅 Tháng {current_month}/{current_year} • Chào buổi {chao}
                </p>
            </div>
        </div>
    """.format(
        current_month=current_month,
        current_year=current_year,
        chao="sáng" if today.hour < 12 else ("chiều" if today.hour < 18 else "tối")
    ), unsafe_allow_html=True)

    st.markdown("<div class='dashboard-grid'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class='stat-card stat-income'>
                <div class='stat-icon' style='background: linear-gradient(135deg, #dcfce7, #bbf7d0);'>💵</div>
                <div class='stat-label'>Tổng thu nhập</div>
                <div class='stat-value' style='color:{COLOR_THU_MAIN};'>{format_vnd(total_income)}</div>
                <div class='stat-trend up'>↑ Tháng này</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class='stat-card stat-expense'>
                <div class='stat-icon' style='background: linear-gradient(135deg, #ffebee, #ffcdd2);'>💸</div>
                <div class='stat-label'>Tổng chi tiêu</div>
                <div class='stat-value' style='color:{COLOR_CHI_MAIN};'>{format_vnd(total_expense)}</div>
                <div class='stat-trend down'>↓ Tháng này</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        balance_color = "stat-balance" if balance >= 0 else "stat-loss"
        balance_icon = "📊" if balance >= 0 else "📉"
        st.markdown(f"""
            <div class='stat-card {balance_color}'>
                <div class='stat-icon' style='background: linear-gradient(135deg, #dbeafe, #bfdbfe);'>{balance_icon}</div>
                <div class='stat-label'>Số dư còn lại</div>
                <div class='stat-value' style='color:{COLOR_DU};'>{format_vnd(balance)}</div>
                <div class='stat-trend {'up' if balance >= 0 else 'down'}'>
                    {'+' if balance >= 0 else ''}{savings_rate:.1f}% tiết kiệm
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        goals = get_savings_goals(user_id)
        total_savings = sum(g['current_amount'] for g in goals)
        st.markdown(f"""
            <div class='stat-card stat-savings'>
                <div class='stat-icon' style='background: linear-gradient(135deg, #f3e8ff, #e9d5ff);'>🏦</div>
                <div class='stat-label'>Tổng quỹ tiết kiệm</div>
                <div class='stat-value' style='color:{COLOR_THU_MAIN};'>{format_vnd(total_savings)}</div>
                <div class='stat-trend up'>🎯 {len(goals)} mục tiêu</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    col_chart, col_recent = st.columns([2, 1])

    with col_chart:
        st.markdown("<h3 style='margin-top: 0;'>📈 Xu hướng thu nhập & chi tiêu</h3>", unsafe_allow_html=True)

        months_data = []
        for i in range(5, -1, -1):
            d = today - timedelta(days=i*30)
            m_summary = get_monthly_summary(user_id, d.year, d.month)
            months_data.append({
                'month': f"{d.month}/{d.year}",
                'Thu nhập': m_summary['income'],
                'Chi tiêu': m_summary['expense']
            })

        df_trend = pd.DataFrame(months_data)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trend['month'], y=df_trend['Thu nhập'],
            mode='lines+markers', name='Thu nhập',
            line=dict(color=COLOR_THU_MAIN, width=4),
            marker=dict(size=10, color=COLOR_THU_MAIN, line=dict(width=2, color='white')),
            fill='tozeroy', fillcolor=COLOR_THU_FILL,
            hovertemplate='<b>%{x}</b><br>💰 Thu nhập: %{y:,.0f} đ<extra></extra>'
        ))
        fig.add_trace(go.Scatter(
            x=df_trend['month'], y=df_trend['Chi tiêu'],
            mode='lines+markers', name='Chi tiêu',
            line=dict(color=COLOR_CHI_MAIN, width=4),
            marker=dict(size=10, color=COLOR_CHI_MAIN, line=dict(width=2, color='white')),
            fill='tozeroy', fillcolor=COLOR_CHI_FILL,
            hovertemplate='<b>%{x}</b><br>💸 Chi tiêu: %{y:,.0f} đ<extra></extra>'
        ))
        fig.update_layout(
            height=350,
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            xaxis=dict(showgrid=False, linecolor='#e2e8f0'),
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9', linecolor='#e2e8f0'),
            hovermode='x unified',
            hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN, font_size=13, font_family='Arial')
        )
        fig.update_xaxes(showspikes=True, spikecolor="#cccccc", spikethickness=1)
        fig.update_yaxes(showspikes=True, spikecolor="#cccccc", spikethickness=1)
        st.plotly_chart(fig, use_container_width=True)

        date_start = f"{current_year}-{current_month:02d}-01"
        if current_month == 12:
            date_end = f"{current_year+1}-01-01"
        else:
            date_end = f"{current_year}-{current_month+1:02d}-01"

        expense_trans = get_transactions(user_id, trans_type='expense',
                                        start_date=date_start, end_date=date_end)

        if expense_trans:
            st.markdown("<h3 style='margin-top: 1rem;'>🥧 Phân bổ chi tiêu</h3>", unsafe_allow_html=True)
            df_exp = pd.DataFrame(expense_trans)
            df_cat = df_exp.groupby('category')['amount'].sum().reset_index()
            df_cat = df_cat.sort_values('amount', ascending=False)

            mau_pie = get_category_colors(df_cat['category'].tolist(), COLORS_CHI)
            fig_pie = px.pie(
                df_cat, values='amount', names='category',
                color_discrete_sequence=mau_pie,
                hole=0.45
            )
            fig_pie.update_traces(
                textposition='outside',
                textinfo='percent+label',
                texttemplate='<b>%{label}</b><br>%{percent}',
                marker=dict(line=dict(color='white', width=2)),
                hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>'
            )
            fig_pie.update_layout(
                height=380,
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=20, b=10),
                showlegend=False,
                font=dict(family="sans-serif", size=12),
                hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_recent:
        st.markdown("<h3 style='margin-top: 0;'>🕐 Giao dịch gần đây</h3>", unsafe_allow_html=True)

        recent_trans = get_transactions(user_id, limit=5)

        if recent_trans:
            for t in recent_trans:
                is_income = t['type'] == 'income'
                icon = "💵" if is_income else "💸"
                mau_nen = "#E8F5E9" if is_income else "#FFEBEE"
                mau_chu = COLOR_THU_MAIN if is_income else COLOR_CHI_MAIN
                bien_trai = COLOR_THU_MAIN if is_income else COLOR_CHI_MAIN
                dau = "+" if is_income else "-"

                st.markdown(f"""
                    <div style='background:{mau_nen}; padding:14px 18px; border-radius:12px; 
                                margin:8px 0; border-left:5px solid {bien_trai};
                                box-shadow: 0 2px 6px rgba(0,0,0,0.05);'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <div>
                                <div style='font-weight:700; font-size:1rem; color:#0f172a;'>{icon} {t['category']}</div>
                                <div style='color:#666; font-size:0.82rem; margin-top:4px;'>{t['date']}</div>
                            </div>
                            <div style='color:{mau_chu}; font-weight:bold; font-size:1.1rem;'>
                                {dau} {format_vnd(t['amount'])}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Chưa có giao dịch nào")

        st.markdown("<h3 style='margin-top: 2rem;'>🎯 Tiến độ tiết kiệm</h3>", unsafe_allow_html=True)

        if goals:
            for goal in goals[:3]:
                progress = (goal['current_amount'] / goal['target_amount'] * 100) if goal['target_amount'] > 0 else 0
                progress = min(progress, 100)
                st.markdown(f"""
                    <div class='saving-item'>
                        <div class='saving-header'>
                            <span class='saving-name'>🎯 {goal['name']}</span>
                            <span class='saving-pct'>{progress:.0f}%</span>
                        </div>
                        <div class='progress-bar-custom'>
                            <div class='progress-fill-custom' style='width: {progress}%;'></div>
                        </div>
                        <div class='saving-amount'>
                            {format_vnd(goal['current_amount'])} / {format_vnd(goal['target_amount'])}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Chưa có mục tiêu tiết kiệm")

def show_transactions_page():
    st.header("💰 Giao dịch hàng ngày")
    user_id = st.session_state['user']['id']
    today = datetime.now().strftime('%Y-%m-%d')
    current_month = datetime.now().strftime('%Y-%m')

    expense_cats = get_user_categories(user_id, 'expense')
    income_cats = get_user_categories(user_id, 'income')

    tab1, tab2, tab3 = st.tabs(["➕ Thêm giao dịch", "📋 Danh sách giao dịch", "📊 Thống kê & Biểu đồ"])

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Thêm giao dịch mới")
            trans_type = st.radio("Loại giao dịch", ["Chi tiêu", "Thu nhập"], horizontal=True)
            trans_type_key = 'expense' if trans_type == "Chi tiêu" else 'income'
            amount = money_input("Số tiền (VNĐ)", min_value=1000, step=1000)
            cats = expense_cats if trans_type_key == 'expense' else income_cats
            cat_names = [cat['name'] for cat in cats]
            category = st.selectbox("Danh mục", cat_names)
            date = st.date_input("Ngày", value=datetime.now())
            note = st.text_area("Ghi chú", height=80)
            if st.button("💾 Lưu giao dịch", type="primary", use_container_width=True):
                success, msg = add_transaction(
                    user_id, trans_type_key, amount, category,
                    date.strftime('%Y-%m-%d'), note
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
        with col2:
            st.subheader("📌 Tổng quan tháng này")
            summary = get_monthly_summary(user_id, datetime.now().year, datetime.now().month)
            total_income = summary['income']
            total_expense = summary['expense']
            balance = total_income - total_expense
            savings_rate = (balance / total_income * 100) if total_income > 0 else 0

            col_a, col_b = st.columns(2)
            with col_a:
                colored_metric("💵 Tổng thu nhập", format_vnd(total_income), COLOR_THU_MAIN)
            with col_b:
                colored_metric("💸 Tổng chi tiêu", format_vnd(total_expense), COLOR_CHI_MAIN)

            col_c, col_d = st.columns(2)
            with col_c:
                du_color = COLOR_DU if balance >= 0 else COLOR_CHI_MAIN
                colored_metric("📊 Số dư", format_vnd(balance), du_color)
            with col_d:
                colored_metric("📈 Tỷ lệ tiết kiệm", f"{savings_rate:.1f}%", COLOR_DU)

    with tab2:
        st.subheader("Lọc giao dịch")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_type = st.selectbox("Loại", ["Tất cả", "Chi tiêu", "Thu nhập"])
        with col2:
            all_cats = get_user_categories(user_id)
            cat_filter = st.selectbox("Danh mục", ["Tất cả"] + [c['name'] for c in all_cats])
        with col3:
            start_date = st.date_input("Từ ngày", value=None)
        with col4:
            end_date = st.date_input("Đến ngày", value=None)

        f_type = 'expense' if filter_type == "Chi tiêu" else ('income' if filter_type == "Thu nhập" else None)
        f_cat = cat_filter if cat_filter != "Tất cả" else None
        f_start = start_date.strftime('%Y-%m-%d') if start_date else None
        f_end = end_date.strftime('%Y-%m-%d') if end_date else None

        transactions = get_transactions(user_id, trans_type=f_type, category=f_cat,
                                        start_date=f_start, end_date=f_end)

        if transactions:
            st.subheader(f"Danh sách giao dịch ({len(transactions)} bản ghi)")

            st.markdown("##### 🎨 Xem dạng thẻ màu (dễ phân biệt Thu/Chi)")
            for t in transactions[:30]:
                is_income = t['type'] == 'income'
                mau_nen = "#E8F5E9" if is_income else "#FFEBEE"
                mau_chu = COLOR_THU_MAIN if is_income else COLOR_CHI_MAIN
                bien_trai = COLOR_THU_MAIN if is_income else COLOR_CHI_MAIN
                dau = "+" if is_income else "-"
                loai_text = "Thu nhập" if is_income else "Chi tiêu"

                st.markdown(f"""
                <div style='background:{mau_nen}; padding:12px 16px; border-radius:10px; 
                            margin:6px 0; border-left:4px solid {bien_trai};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; gap:12px;'>
                        <div style='flex:2;'>
                            <div style='font-weight:600; color:#0f172a;'>{t['category']}</div>
                            <div style='color:#666; font-size:0.85rem;'>{t['date']} • {t['note'] or ''}</div>
                        </div>
                        <div style='flex:1; text-align:center;'>
                            <span style='background:{mau_chu}20; color:{mau_chu}; 
                                  padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.9rem;'>
                                {loai_text}
                            </span>
                        </div>
                        <div style='flex:1; text-align:right; color:{mau_chu}; font-weight:bold; font-size:1.1rem;'>
                            {dau} {format_vnd(t['amount'])}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            if len(transactions) > 30:
                st.caption(f"Đang hiển thị 30 / {len(transactions)} bản ghi. Xem đầy đủ dạng bảng bên dưới.")

            st.markdown("##### 📊 Xem dạng bảng")
            df = pd.DataFrame(transactions)
            df_display = df[['date', 'type', 'category', 'amount', 'note']].copy()
            df_display['type'] = df_display['type'].map({'expense': '💸 Chi tiêu', 'income': '💵 Thu nhập'})
            df_display['amount'] = df_display['amount'].apply(format_vnd)
            df_display.columns = ['Ngày', 'Loại', 'Danh mục', 'Số tiền', 'Ghi chú']
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            st.subheader("✏️ Sửa / Xóa giao dịch")
            trans_options = {f"{t['date']} - {t['category']} - {format_vnd(t['amount'])}": t['id']
                             for t in transactions[:50]}
            selected_trans = st.selectbox("Chọn giao dịch", list(trans_options.keys()))

            if selected_trans:
                trans_id = trans_options[selected_trans]
                trans = next(t for t in transactions if t['id'] == trans_id)

                col1, col2 = st.columns([3, 1])
                with col1:
                    new_type = st.radio("Loại", ["Chi tiêu", "Thu nhập"],
                                        index=0 if trans['type'] == 'expense' else 1,
                                        key=f"edit_type_{trans_id}", horizontal=True)
                    new_type_key = 'expense' if new_type == "Chi tiêu" else 'income'
                    new_amount = money_input("Số tiền", value=trans['amount'],
                                             min_value=1000, step=1000, key=f"edit_amt_{trans_id}")
                    edit_cats = expense_cats if new_type_key == 'expense' else income_cats
                    edit_cat_names = [c['name'] for c in edit_cats]
                    current_cat_idx = edit_cat_names.index(trans['category']) if trans['category'] in edit_cat_names else 0
                    new_category = st.selectbox("Danh mục", edit_cat_names,
                                                index=current_cat_idx, key=f"edit_cat_{trans_id}")
                    new_date = st.date_input("Ngày", value=datetime.strptime(trans['date'], '%Y-%m-%d'),
                                             key=f"edit_date_{trans_id}")
                    new_note = st.text_area("Ghi chú", value=trans['note'] or "",
                                            key=f"edit_note_{trans_id}", height=60)
                    if st.button("💾 Cập nhật", key=f"update_btn_{trans_id}"):
                        success, msg = update_transaction(
                            trans_id, user_id, new_type_key, new_amount, new_category,
                            new_date.strftime('%Y-%m-%d'), new_note
                        )
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with col2:
                    if st.button("🗑️ Xóa", key=f"delete_btn_{trans_id}", type="secondary"):
                        if delete_transaction(trans_id, user_id):
                            st.success("Đã xóa!")
                            st.rerun()
                        else:
                            st.error("Lỗi xóa!")
        else:
            st.info("Chưa có giao dịch nào.")

    with tab3:
        st.markdown("<h2 style='color:#2E7D32; margin-bottom:1rem;'>📊 Biểu đồ phân tích</h2>", unsafe_allow_html=True)

        year = datetime.now().year
        month = datetime.now().month

        date_start = f"{year}-{month:02d}-01"
        if month == 12:
            date_end = f"{year+1}-01-01"
        else:
            date_end = f"{year}-{month+1:02d}-01"

        expense_trans = get_transactions(user_id, trans_type='expense',
                                         start_date=date_start, end_date=date_end)
        income_trans = get_transactions(user_id, trans_type='income',
                                        start_date=date_start, end_date=date_end)
        summary = get_monthly_summary(user_id, year, month)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            colored_metric("💵 Tổng thu", format_vnd(summary['income']), COLOR_THU_MAIN)
        with col2:
            colored_metric("💸 Tổng chi", format_vnd(summary['expense']), COLOR_CHI_MAIN)
        with col3:
            balance = summary['income'] - summary['expense']
            du_color = COLOR_DU if balance >= 0 else COLOR_CHI_MAIN
            colored_metric("📊 Số dư", format_vnd(balance), du_color)
        with col4:
            rate = (balance / summary['income'] * 100) if summary['income'] > 0 else 0
            colored_metric("📈 Tỷ lệ tiết kiệm", f"{rate:.1f}%", COLOR_DU)

        st.markdown("---")

        r1_col1, r1_col2 = st.columns(2)

        with r1_col1:
            st.markdown("### 1. Phân bổ thu nhập")
            if income_trans:
                df_inc = pd.DataFrame(income_trans)
                df_thu = df_inc.groupby('category')['amount'].sum().sort_values(ascending=False)
                mau_pie_thu = get_category_colors(df_thu.index.tolist(), COLORS_THU)
                fig1 = px.pie(
                    values=df_thu.values,
                    names=df_thu.index,
                    color_discrete_sequence=mau_pie_thu,
                    hole=0.4
                )
                fig1.update_traces(
                    textposition="outside",
                    textinfo="percent+label",
                    hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>'
                )
                fig1.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=20, b=20, l=10, r=10),
                    legend=dict(orientation="v", y=0.5, x=1, yanchor="middle"),
                    height=400,
                    font=dict(family="sans-serif", size=12),
                    hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_THU_MAIN)
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Chưa có thu nhập trong tháng")

        with r1_col2:
            st.markdown("### 2. Phân bổ chi tiêu")
            if expense_trans:
                df_exp = pd.DataFrame(expense_trans)
                df_chi = df_exp.groupby('category')['amount'].sum().sort_values(ascending=False)
                mau_pie = get_category_colors(df_chi.index.tolist(), COLORS_CHI)
                fig2 = px.pie(
                    values=df_chi.values,
                    names=df_chi.index,
                    color_discrete_sequence=mau_pie,
                    hole=0.4
                )
                fig2.update_traces(
                    textposition="outside",
                    textinfo="percent+label",
                    hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>'
                )
                fig2.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=20, b=20, l=10, r=10),
                    legend=dict(orientation="v", y=0.5, x=1, yanchor="middle"),
                    height=400,
                    font=dict(family="sans-serif", size=12),
                    hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Chưa có chi tiêu trong tháng")

        st.markdown("---")

        r2_col1, r2_col2 = st.columns(2)

        with r2_col1:
            st.markdown("### 3. Top danh mục chi tiêu nhiều nhất")
            if expense_trans:
                df_exp3 = pd.DataFrame(expense_trans)
                df_chi3 = df_exp3.groupby('category')['amount'].sum()
                total_chi = df_chi3.sum()

                df_top = df_chi3.reset_index()
                df_top.columns = ["Danh mục", "Số tiền"]
                df_top = df_top.sort_values("Số tiền", ascending=False).head(5)
                df_top["Tỷ lệ"] = (df_top["Số tiền"] / total_chi * 100).round(1)

                fig3 = px.bar(
                    df_top,
                    y="Danh mục",
                    x="Số tiền",
                    orientation="h",
                    text=df_top["Tỷ lệ"].astype(str) + "%",
                    color="Danh mục",
                    color_discrete_map=COLORS_CHI
                )
                fig3.update_traces(
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(color="white", size=12, family='Arial'),
                    hovertemplate='<b>%{y}</b><br>Số tiền: %{x:,.0f} đ<br>Tỷ lệ: %{text}<extra></extra>'
                )
                fig3.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    height=400,
                    xaxis_title="Số tiền (VNĐ)",
                    yaxis_title="",
                    margin=dict(t=10, b=10, l=10, r=10),
                    font=dict(family="sans-serif", size=12),
                    hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu chi tiêu")

        with r2_col2:
            st.markdown("### 4. So sánh thu nhập & chi tiêu 6 tháng gần nhất")
            months_data_6 = []
            for i in range(5, -1, -1):
                d = datetime.now() - timedelta(days=i*30)
                m_summary = get_monthly_summary(user_id, d.year, d.month)
                months_data_6.append({
                    'Tháng': f"T{d.month}",
                    'Thu nhập': m_summary['income'],
                    'Chi tiêu': m_summary['expense']
                })
            df_6thang = pd.DataFrame(months_data_6)
            fig4 = px.bar(
                df_6thang,
                x='Tháng',
                y=['Thu nhập', 'Chi tiêu'],
                barmode='group',
                color_discrete_map={
                    'Thu nhập': COLOR_THU_MAIN,
                    'Chi tiêu': COLOR_CHI_MAIN
                }
            )
            fig4.update_traces(
                hovertemplate='<b>%{x}</b><br>%{fullData.name}: %{y:,.0f} đ<extra></extra>'
            )
            fig4.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
                margin=dict(t=30, b=0, l=0, r=0),
                height=400,
                xaxis_title='',
                yaxis_title='Số tiền (VNĐ)',
                font=dict(family="sans-serif", size=12),
                hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
            )
            st.plotly_chart(fig4, use_container_width=True)

# ⬇️⬇️⬇️ PHẦN 2 TIẾP TỤC TỪ show_savings_page() ⬇️⬇️⬇️
def show_savings_page():
    st.header("🏦 Quản lý tiết kiệm")
    user_id = st.session_state['user']['id']
    tab1, tab2, tab3 = st.tabs(["🎯 Mục tiêu tiết kiệm", "📊 Thống kê & Biểu đồ", "🧮 Tính lãi kép"])

    with tab1:
        st.subheader("Tạo mục tiêu mới")
        col1, col2 = st.columns([1, 1])
        with col1:
            goal_name = st.text_input("Tên mục tiêu", placeholder="Ví dụ: Mua xe, Du lịch...")
            target_amount = money_input("Số tiền mong muốn (VNĐ)", min_value=1000000, step=1000000)
            deadline = st.date_input("Ngày hoàn thành", min_value=datetime.now())
            description = st.text_area("Mô tả", height=80)
            if st.button("➕ Tạo mục tiêu", type="primary"):
                if not goal_name.strip():
                    st.error("Vui lòng nhập tên mục tiêu!")
                else:
                    success, msg = add_savings_goal(
                        user_id, goal_name, target_amount,
                        deadline.strftime('%Y-%m-%d'), description
                    )
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        with col2:
            goals = get_savings_goals(user_id)
            total_savings = sum(g['current_amount'] for g in goals)
            total_target = sum(g['target_amount'] for g in goals)
            st.metric("💰 Tổng quỹ tiết kiệm", format_vnd(total_savings))
            if total_target > 0:
                progress = (total_savings / total_target) * 100
                st.progress(min(progress / 100, 1.0))
                st.caption(f"Đạt {progress:.1f}% mục tiêu tổng cộng")

        st.subheader("📋 Danh sách mục tiêu")
        goals = get_savings_goals(user_id)
        if goals:
            for goal in goals:
                with st.expander(f"🎯 {goal['name']} - {format_vnd(goal['current_amount'])} / {format_vnd(goal['target_amount'])}"):
                    progress = (goal['current_amount'] / goal['target_amount']) * 100 if goal['target_amount'] > 0 else 0
                    st.progress(min(progress / 100, 1.0))
                    st.write(f"**Tiến độ:** {progress:.1f}%")
                    st.write(f"**Còn lại:** {format_vnd(goal['target_amount'] - goal['current_amount'])}")
                    if goal['deadline']:
                        st.write(f"**Hạn chót:** {goal['deadline']}")
                        remaining = goal['target_amount'] - goal['current_amount']
                        days_left = (datetime.strptime(goal['deadline'], '%Y-%m-%d') - datetime.now()).days
                        if days_left > 0 and remaining > 0:
                            monthly_needed = remaining / (days_left / 30)
                            st.info(f"Cần tiết kiệm khoảng **{format_vnd(monthly_needed)}** mỗi tháng để hoàn thành đúng hạn.")
                    if goal['description']:
                        st.write(f"**Mô tả:** {goal['description']}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        deposit_amount = money_input("Nạp tiền", min_value=0, step=100000, key=f"dep_{goal['id']}")
                        if st.button("📥 Nạp", key=f"dep_btn_{goal['id']}"):
                            if deposit_amount > 0:
                                success, msg = update_savings_goal(goal['id'], user_id, deposit_amount, 'deposit', 'Nạp tiền')
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    with col2:
                        withdraw_amount = money_input("Rút tiền", min_value=0, step=100000, key=f"wit_{goal['id']}")
                        if st.button("📤 Rút", key=f"wit_btn_{goal['id']}"):
                            if withdraw_amount > 0:
                                success, msg = update_savings_goal(goal['id'], user_id, withdraw_amount, 'withdraw', 'Rút tiền')
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    with col3:
                        if st.button("🗑️ Xóa mục tiêu", key=f"del_goal_{goal['id']}"):
                            if delete_savings_goal(goal['id'], user_id):
                                st.success("Đã xóa!")
                                st.rerun()
                    st.subheader("Lịch sử giao dịch")
                    history = get_savings_transactions(user_id, goal['id'])
                    if history:
                        df_hist = pd.DataFrame(history)
                        df_hist['type'] = df_hist['type'].map({'deposit': '📥 Nạp', 'withdraw': '📤 Rút'})
                        df_hist['amount'] = df_hist['amount'].apply(format_vnd)
                        df_display = df_hist[['date', 'type', 'amount', 'note']]
                        df_display.columns = ['Ngày', 'Loại', 'Số tiền', 'Ghi chú']
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có mục tiêu tiết kiệm nào. Hãy tạo mục tiêu đầu tiên!")

    with tab2:
        st.subheader("📊 Biểu đồ tiết kiệm")
        goals = get_savings_goals(user_id)
        if goals:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📊 Tiến độ các mục tiêu")
                df_goals = pd.DataFrame(goals)
                df_goals['progress'] = (df_goals['current_amount'] / df_goals['target_amount']) * 100
                fig = go.Figure()
                for _, row in df_goals.iterrows():
                    fig.add_trace(go.Bar(
                        x=[row['name']], y=[min(row['progress'], 100)],
                        name=row['name'],
                        text=[f"{row['progress']:.1f}%"],
                        textposition='auto',
                        hovertemplate='<b>%{x}</b><br>Tiến độ: %{y:.1f}%<extra></extra>'
                    ))
                fig.update_layout(
                    title='Tiến độ hoàn thành mục tiêu (%)',
                    yaxis_title='Tiến độ (%)',
                    showlegend=False,
                    yaxis_range=[0, 100],
                    hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_THU_MAIN)
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("🥧 Phân bổ quỹ tiết kiệm")
                df_allocation = df_goals[df_goals['current_amount'] > 0]
                if not df_allocation.empty:
                    mau_pie = get_category_colors(df_allocation['name'].tolist(), COLORS_THU)
                    fig = px.pie(df_allocation, values='current_amount', names='name',
                                 title='Phân bổ theo mục tiêu',
                                 color_discrete_sequence=mau_pie)
                    fig.update_traces(
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Chưa có tiền trong quỹ tiết kiệm.")

            st.subheader("📜 Lịch sử nạp/rút chung")
            all_history = get_savings_transactions(user_id)
            if all_history:
                df_all_hist = pd.DataFrame(all_history)
                df_all_hist['type'] = df_all_hist['type'].map({'deposit': '📥 Nạp', 'withdraw': '📤 Rút'})
                df_all_hist['amount'] = df_all_hist['amount'].apply(format_vnd)
                df_display = df_all_hist[['date', 'goal_name', 'type', 'amount', 'note']]
                df_display.columns = ['Ngày', 'Mục tiêu', 'Loại', 'Số tiền', 'Ghi chú']
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu tiết kiệm.")

    with tab3:
        st.subheader("🧮 Tính toán lãi kép")
        col1, col2 = st.columns(2)
        with col1:
            principal = money_input("Số tiền gốc ban đầu (VNĐ)", min_value=0, step=1000000, value=10000000)
            monthly_contribution = money_input("Số tiền nạp thêm mỗi tháng (VNĐ)", min_value=0, step=100000, value=1000000)
            annual_rate = st.number_input("Lãi suất năm (%)", min_value=0.0, max_value=30.0, step=0.1, value=6.0)
            years = st.number_input("Số năm gửi", min_value=1, max_value=50, step=1, value=10)
        with col2:
            compound_result = calculate_compound_interest(principal, annual_rate, years, monthly_contribution)
            simple_result = calculate_simple_interest(principal + monthly_contribution * 12 * years, annual_rate, 1)
            total_contributed = principal + monthly_contribution * 12 * years
            st.metric("💰 Số tiền gốc đã góp", format_vnd(total_contributed))
            st.metric("📈 Giá trị sau lãi kép", format_vnd(compound_result))
            st.metric("💎 Lãi nhận được", format_vnd(compound_result - total_contributed))

        st.subheader("📈 Đường cong tăng trưởng lãi kép")
        growth_data = []
        for y in range(years + 1):
            val = calculate_compound_interest(principal, annual_rate, y, monthly_contribution)
            simple_val = principal + monthly_contribution * 12 * y
            growth_data.append({'Năm': y, 'Lãi kép': val, 'Tiền gốc': simple_val})
        df_growth = pd.DataFrame(growth_data)
        fig = px.line(df_growth, x='Năm', y=['Lãi kép', 'Tiền gốc'],
                      title='Tăng trưởng theo thời gian',
                      labels={'value': 'Số tiền (VNĐ)', 'variable': 'Loại'},
                      color_discrete_map={'Lãi kép': COLOR_THU_MAIN, 'Tiền gốc': '#94a3b8'})
        fig.update_traces(hovertemplate='<b>Năm %{x}</b><br>%{y:,.0f} đ<extra></extra>')
        fig.update_layout(hovermode='x unified',
                          hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_THU_MAIN))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📊 So sánh Lãi đơn vs Lãi kép qua các năm")
        compare_data = []
        for y in range(1, years + 1, max(1, years // 10)):
            compound = calculate_compound_interest(principal, annual_rate, y, monthly_contribution)
            total_in = principal + monthly_contribution * 12 * y
            simple = total_in * (1 + annual_rate / 100 * y)
            compare_data.append({
                'Năm': y,
                'Tiền gốc góp': format_vnd(total_in),
                'Lãi đơn': format_vnd(simple),
                'Lãi kép': format_vnd(compound),
                'Chênh lệch': format_vnd(compound - simple)
            })
        df_compare = pd.DataFrame(compare_data)
        st.dataframe(df_compare, use_container_width=True, hide_index=True)

def show_investments_page():
    st.header("📈 Quản lý đầu tư")
    user_id = st.session_state['user']['id']
    tab1, tab2, tab3 = st.tabs(["💼 Danh mục đầu tư", "📊 Thống kê & Biểu đồ", "➕ Thêm đầu tư"])

    with tab3:
        st.subheader("Thêm khoản đầu tư mới")
        col1, col2 = st.columns(2)
        with col1:
            inv_type = st.selectbox("Loại hình đầu tư", INVESTMENT_TYPES)
            inv_name = st.text_input("Tên khoản đầu tư", placeholder="Ví dụ: Cổ phiếu VNM, Quỹ DCBC...")
            principal = money_input("Số tiền gốc (VNĐ)", min_value=1000000, step=1000000)
        with col2:
            current_value = money_input("Giá trị hiện tại (VNĐ)", min_value=0, step=1000000)
            invest_date = st.date_input("Ngày đầu tư", value=datetime.now())
            expected_return = st.number_input("Lợi nhuận kỳ vọng (%)", min_value=0.0, step=0.1)
        if st.button("💾 Lưu khoản đầu tư", type="primary", use_container_width=True):
            if not inv_name.strip():
                st.error("Vui lòng nhập tên khoản đầu tư!")
            else:
                success, msg = add_investment(
                    user_id, inv_type, inv_name, principal,
                    current_value if current_value > 0 else principal,
                    invest_date.strftime('%Y-%m-%d'), expected_return
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    with tab1:
        investments = get_investments(user_id)
        if investments:
            total_principal = sum(inv['principal_amount'] for inv in investments)
            total_current = sum(inv['current_value'] for inv in investments)
            total_profit = total_current - total_principal
            profit_pct = (total_profit / total_principal * 100) if total_principal > 0 else 0
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Tổng tiền gốc", format_vnd(total_principal))
            with col2:
                st.metric("📊 Giá trị hiện tại", format_vnd(total_current))
            with col3:
                delta_color = "normal" if total_profit >= 0 else "inverse"
                st.metric("📈 Lợi nhuận", format_vnd(total_profit),
                          f"{profit_pct:+.1f}%", delta_color=delta_color)
            with col4:
                total_years = 0
                total_cagr = 0
                for inv in investments:
                    days = (datetime.now() - datetime.strptime(inv['invest_date'], '%Y-%m-%d')).days
                    years = days / 365.25
                    if years > 0:
                        cagr = calculate_cagr(inv['principal_amount'], inv['current_value'], years)
                        total_cagr += cagr
                        total_years += 1
                avg_cagr = total_cagr / total_years if total_years > 0 else 0
                st.metric("📅 CAGR trung bình", f"{avg_cagr:.1f}%")

            st.subheader("📋 Danh sách khoản đầu tư")
            for inv in investments:
                profit = inv['current_value'] - inv['principal_amount']
                profit_pct = (profit / inv['principal_amount'] * 100) if inv['principal_amount'] > 0 else 0
                days_held = (datetime.now() - datetime.strptime(inv['invest_date'], '%Y-%m-%d')).days
                years_held = days_held / 365.25
                cagr = calculate_cagr(inv['principal_amount'], inv['current_value'], years_held)
                status_icon = "🟢" if inv['status'] == 'holding' else "🔴"
                status_text = "Đang nắm giữ" if inv['status'] == 'holding' else "Đã bán"
                expander_title = f"{status_icon} [{inv['type']}] {inv['name']} - {format_vnd(inv['current_value'])}"
                if profit >= 0:
                    expander_title += f" 🟢 +{format_vnd(profit)} ({profit_pct:+.1f}%)"
                else:
                    expander_title += f" 🔴 {format_vnd(profit)} ({profit_pct:+.1f}%)"
                with st.expander(expander_title):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Loại hình:** {inv['type']}")
                        st.write(f"**Ngày đầu tư:** {inv['invest_date']}")
                        st.write(f"**Thời gian nắm giữ:** {years_held:.1f} năm")
                    with col2:
                        st.write(f"**Tiền gốc:** {format_vnd(inv['principal_amount'])}")
                        st.write(f"**Giá trị hiện tại:** {format_vnd(inv['current_value'])}")
                        st.write(f"**Lợi nhuận kỳ vọng:** {inv['expected_return']}%")
                    with col3:
                        profit_color = "🟢" if profit >= 0 else "🔴"
                        st.write(f"**Lợi nhuận:** {profit_color} {format_vnd(profit)} ({profit_pct:+.1f}%)")
                        st.write(f"**CAGR:** {cagr:.1f}%/năm")
                        st.write(f"**Trạng thái:** {status_text}")
                    if inv['status'] == 'holding':
                        st.subheader("Cập nhật giá trị")
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            new_value = money_input("Giá trị mới", min_value=0, step=100000,
                                                    value=inv['current_value'], key=f"new_val_{inv['id']}")
                        with col_b:
                            update_note = st.text_input("Ghi chú", key=f"upd_note_{inv['id']}")
                        with col_c:
                            if st.button("💾 Cập nhật", key=f"upd_btn_{inv['id']}"):
                                success, msg = update_investment_value(inv['id'], user_id, new_value, update_note)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        col_d, col_e = st.columns(2)
                        with col_d:
                            if st.button("✅ Đánh dấu đã bán", key=f"sell_btn_{inv['id']}"):
                                if sell_investment(inv['id'], user_id):
                                    st.success("Đã cập nhật trạng thái!")
                                    st.rerun()
                        with col_e:
                            if st.button("🗑️ Xóa", key=f"del_inv_{inv['id']}"):
                                if delete_investment(inv['id'], user_id):
                                    st.success("Đã xóa!")
                                    st.rerun()
                    st.subheader("📜 Lịch sử cập nhật giá trị")
                    updates = get_investment_updates(inv['id'])
                    if updates:
                        df_updates = pd.DataFrame(updates)
                        df_updates['value'] = df_updates['value'].apply(format_vnd)
                        df_display = df_updates[['date', 'value', 'note']]
                        df_display.columns = ['Ngày', 'Giá trị', 'Ghi chú']
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có khoản đầu tư nào. Hãy thêm khoản đầu tư đầu tiên!")

    with tab2:
        st.subheader("📊 Phân tích danh mục đầu tư")
        investments = get_investments(user_id)
        if investments:
            df_inv = pd.DataFrame(investments)
            df_inv['profit'] = df_inv['current_value'] - df_inv['principal_amount']
            df_inv['profit_pct'] = (df_inv['profit'] / df_inv['principal_amount'] * 100)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🥧 Phân bổ theo loại hình")
                df_type = df_inv.groupby('type')['current_value'].sum().reset_index()
                fig = px.pie(df_type, values='current_value', names='type',
                             title='Phân bổ danh mục',
                             color_discrete_sequence=['#f59e0b', '#84cc16', '#0ea5e9', '#f97316',
                                                      '#eab308', '#22c55e', '#38bdf8', '#fb923c'])
                fig.update_traces(textinfo='percent+label',
                                  hovertemplate='<b>%{label}</b><br>Giá trị: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("📊 Lợi nhuận từng khoản")
                df_inv_sorted = df_inv.sort_values('profit', ascending=True)
                colors = [COLOR_THU_MAIN if p >= 0 else COLOR_CHI_MAIN for p in df_inv_sorted['profit']]
                fig = go.Figure(go.Bar(
                    x=df_inv_sorted['profit'],
                    y=df_inv_sorted['name'],
                    orientation='h',
                    marker_color=colors,
                    text=df_inv_sorted['profit_pct'].apply(lambda x: f"{x:+.1f}%"),
                    textposition='auto',
                    hovertemplate='<b>%{y}</b><br>Lợi nhuận: %{x:,.0f} đ<extra></extra>'
                ))
                fig.update_layout(title='Lợi nhuận/Thua lỗ', xaxis_title='Số tiền (VNĐ)',
                                  hoverlabel=dict(bgcolor='#FFF8E1'))
                st.plotly_chart(fig, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Top 3 sinh lời tốt nhất")
                top_profit = df_inv.nlargest(3, 'profit_pct')
                for _, row in top_profit.iterrows():
                    st.success(f"**{row['name']}**: +{row['profit_pct']:.1f}% ({format_vnd(row['profit'])})")
            with col2:
                st.subheader("⚠️ Top 3 thua lỗ nhiều nhất")
                top_loss = df_inv.nsmallest(3, 'profit_pct')
                for _, row in top_loss.iterrows():
                    if row['profit_pct'] < 0:
                        st.error(f"**{row['name']}**: {row['profit_pct']:.1f}% ({format_vnd(row['profit'])})")

            st.subheader("📊 Tỷ trọng từng khoản trong danh mục")
            df_inv['weight'] = (df_inv['current_value'] / df_inv['current_value'].sum() * 100)
            df_weight = df_inv.sort_values('weight', ascending=True)
            fig = go.Figure(go.Bar(
                x=df_weight['weight'],
                y=df_weight['name'],
                orientation='h',
                text=df_weight['weight'].apply(lambda x: f"{x:.1f}%"),
                textposition='auto',
                marker_color='#c2410c',
                hovertemplate='<b>%{y}</b><br>Tỷ trọng: %{x:.1f}%<extra></extra>'
            ))
            fig.update_layout(title='Tỷ trọng trong danh mục (%)', xaxis_title='Tỷ trọng (%)',
                              hoverlabel=dict(bgcolor='#FFF8E1'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu đầu tư.")

# ============================================================
# BÁO CÁO & XUẤT DỮ LIỆU
# ✅ ĐÃ COPY 4 BIỂU ĐỒ TỪ TAB THỐNG KÊ VÀO TAB BÁO CÁO TỔNG HỢP
# ============================================================

def show_reports_page():
    st.header("📊 Báo cáo & Xuất dữ liệu")
    user_id = st.session_state['user']['id']
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Báo cáo tổng hợp", "💾 Xuất dữ liệu", "🎯 Ngân sách", "🔔 Nhắc nhở"])

    with tab1:
        st.subheader("Báo cáo tài chính")
        col1, col2 = st.columns(2)
        with col1:
            report_year = st.selectbox("Năm", range(datetime.now().year, datetime.now().year - 5, -1), key="rp_year")
        with col2:
            report_type = st.radio("Loại báo cáo", ["Tháng", "Năm"], horizontal=True, key="rp_type")

        if report_type == "Tháng":
            report_month = st.selectbox("Tháng", range(1, 13), index=datetime.now().month - 1, key="rp_month")
            summary = get_monthly_summary(user_id, report_year, report_month)
            total_income = summary['income']
            total_expense = summary['expense']
            balance = total_income - total_expense
            st.subheader(f"Báo cáo tháng {report_month}/{report_year}")

            # === 3 thẻ tóm tắt ===
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div style='background:white; padding:24px; border-radius:16px; 
                            box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:5px solid {COLOR_THU_MAIN};'>
                    <div style='color:#666; font-size:0.9rem;'>💵 Tổng thu nhập</div>
                    <div style='font-size:1.8rem; font-weight:bold; color:{COLOR_THU_MAIN}; margin-top:8px;'>
                        {format_vnd(total_income)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style='background:white; padding:24px; border-radius:16px; 
                            box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:5px solid {COLOR_CHI_MAIN};'>
                    <div style='color:#666; font-size:0.9rem;'>💸 Tổng chi tiêu</div>
                    <div style='font-size:1.8rem; font-weight:bold; color:{COLOR_CHI_MAIN}; margin-top:8px;'>
                        {format_vnd(total_expense)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                du_color = COLOR_DU if balance >= 0 else COLOR_CHI_MAIN
                st.markdown(f"""
                <div style='background:white; padding:24px; border-radius:16px; 
                            box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:5px solid {du_color};'>
                    <div style='color:#666; font-size:0.9rem;'>📊 Số dư</div>
                    <div style='font-size:1.8rem; font-weight:bold; color:{du_color}; margin-top:8px;'>
                        {format_vnd(balance)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # === Chuẩn bị dữ liệu ===
            date_start = f"{report_year}-{report_month:02d}-01"
            if report_month == 12:
                date_end = f"{report_year+1}-01-01"
            else:
                date_end = f"{report_year}-{report_month+1:02d}-01"

            expense_trans = get_transactions(user_id, trans_type='expense',
                                             start_date=date_start, end_date=date_end)
            income_trans = get_transactions(user_id, trans_type='income',
                                            start_date=date_start, end_date=date_end)

            # === Bảng chi tiết ===
            st.subheader("Chi tiết chi tiêu theo danh mục")
            if expense_trans:
                df_exp = pd.DataFrame(expense_trans)
                df_cat = df_exp.groupby('category')['amount'].sum().reset_index()
                df_cat = df_cat.sort_values('amount', ascending=False)
                df_cat_display = df_cat.copy()
                df_cat_display['amount'] = df_cat_display['amount'].apply(format_vnd)
                df_cat_display.columns = ['Danh mục', 'Tổng chi']
                st.dataframe(df_cat_display, use_container_width=True, hide_index=True)
            else:
                st.info("Không có chi tiêu nào trong kỳ này.")

            # ==========================================================
            # 4 BIỂU ĐỒ PHÂN TÍCH (COPY Y HỆT TAB THỐNG KÊ)
            # ==========================================================
            st.markdown("---")
            st.markdown("<h2 style='color:#2E7D32; margin-bottom:1rem;'>📊 Biểu đồ phân tích</h2>", unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                colored_metric("💵 Tổng thu", format_vnd(total_income), COLOR_THU_MAIN)
            with col2:
                colored_metric("💸 Tổng chi", format_vnd(total_expense), COLOR_CHI_MAIN)
            with col3:
                du_color = COLOR_DU if balance >= 0 else COLOR_CHI_MAIN
                colored_metric("📊 Số dư", format_vnd(balance), du_color)
            with col4:
                rate = (balance / total_income * 100) if total_income > 0 else 0
                colored_metric("📈 Tỷ lệ tiết kiệm", f"{rate:.1f}%", COLOR_DU)

            st.markdown("---")

            # HÀNG 1
            r1_col1, r1_col2 = st.columns(2)

            with r1_col1:
                st.markdown("### 1. Phân bổ thu nhập")
                if income_trans:
                    df_inc = pd.DataFrame(income_trans)
                    df_thu = df_inc.groupby('category')['amount'].sum().sort_values(ascending=False)
                    mau_pie_thu = get_category_colors(df_thu.index.tolist(), COLORS_THU)
                    fig1 = px.pie(
                        values=df_thu.values,
                        names=df_thu.index,
                        color_discrete_sequence=mau_pie_thu,
                        hole=0.4
                    )
                    fig1.update_traces(
                        textposition="outside",
                        textinfo="percent+label",
                        hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>'
                    )
                    fig1.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(t=20, b=20, l=10, r=10),
                        legend=dict(orientation="v", y=0.5, x=1, yanchor="middle"),
                        height=400,
                        font=dict(family="sans-serif", size=12),
                        hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_THU_MAIN)
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.info("Chưa có thu nhập trong tháng")

            with r1_col2:
                st.markdown("### 2. Phân bổ chi tiêu")
                if expense_trans:
                    df_exp2 = pd.DataFrame(expense_trans)
                    df_chi = df_exp2.groupby('category')['amount'].sum().sort_values(ascending=False)
                    mau_pie = get_category_colors(df_chi.index.tolist(), COLORS_CHI)
                    fig2 = px.pie(
                        values=df_chi.values,
                        names=df_chi.index,
                        color_discrete_sequence=mau_pie,
                        hole=0.4
                    )
                    fig2.update_traces(
                        textposition="outside",
                        textinfo="percent+label",
                        hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} đ<br>Tỷ lệ: %{percent}<extra></extra>'
                    )
                    fig2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(t=20, b=20, l=10, r=10),
                        legend=dict(orientation="v", y=0.5, x=1, yanchor="middle"),
                        height=400,
                        font=dict(family="sans-serif", size=12),
                        hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Chưa có chi tiêu trong tháng")

            st.markdown("---")

            # HÀNG 2
            r2_col1, r2_col2 = st.columns(2)

            with r2_col1:
                st.markdown("### 3. Top danh mục chi tiêu nhiều nhất")
                if expense_trans:
                    df_exp3 = pd.DataFrame(expense_trans)
                    df_chi3 = df_exp3.groupby('category')['amount'].sum()
                    total_chi = df_chi3.sum()

                    df_top = df_chi3.reset_index()
                    df_top.columns = ["Danh mục", "Số tiền"]
                    df_top = df_top.sort_values("Số tiền", ascending=False).head(5)
                    df_top["Tỷ lệ"] = (df_top["Số tiền"] / total_chi * 100).round(1)

                    fig3 = px.bar(
                        df_top,
                        y="Danh mục",
                        x="Số tiền",
                        orientation="h",
                        text=df_top["Tỷ lệ"].astype(str) + "%",
                        color="Danh mục",
                        color_discrete_map=COLORS_CHI
                    )
                    fig3.update_traces(
                        textposition="inside",
                        insidetextanchor="middle",
                        textfont=dict(color="white", size=12, family='Arial'),
                        hovertemplate='<b>%{y}</b><br>Số tiền: %{x:,.0f} đ<br>Tỷ lệ: %{text}<extra></extra>'
                    )
                    fig3.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        height=400,
                        xaxis_title="Số tiền (VNĐ)",
                        yaxis_title="",
                        margin=dict(t=10, b=10, l=10, r=10),
                        font=dict(family="sans-serif", size=12),
                        hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("Chưa có dữ liệu chi tiêu")

            with r2_col2:
                st.markdown("### 4. So sánh thu nhập & chi tiêu 6 tháng gần nhất")
                months_data_6 = []
                for i in range(5, -1, -1):
                    d = datetime.now() - timedelta(days=i*30)
                    m_summary = get_monthly_summary(user_id, d.year, d.month)
                    months_data_6.append({
                        'Tháng': f"T{d.month}",
                        'Thu nhập': m_summary['income'],
                        'Chi tiêu': m_summary['expense']
                    })
                df_6thang = pd.DataFrame(months_data_6)
                fig4 = px.bar(
                    df_6thang,
                    x='Tháng',
                    y=['Thu nhập', 'Chi tiêu'],
                    barmode='group',
                    color_discrete_map={
                        'Thu nhập': COLOR_THU_MAIN,
                        'Chi tiêu': COLOR_CHI_MAIN
                    }
                )
                fig4.update_traces(
                    hovertemplate='<b>%{x}</b><br>%{fullData.name}: %{y:,.0f} đ<extra></extra>'
                )
                fig4.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
                    margin=dict(t=30, b=0, l=0, r=0),
                    height=400,
                    xaxis_title='',
                    yaxis_title='Số tiền (VNĐ)',
                    font=dict(family="sans-serif", size=12),
                    hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN)
                )
                st.plotly_chart(fig4, use_container_width=True)

        else:
            # === BÁO CÁO NĂM ===
            st.subheader(f"Báo cáo năm {report_year}")
            yearly_data = []
            for m in range(1, 13):
                m_summary = get_monthly_summary(user_id, report_year, m)
                yearly_data.append({
                    'Tháng': m,
                    'Thu nhập': m_summary['income'],
                    'Chi tiêu': m_summary['expense'],
                    'Số dư': m_summary['income'] - m_summary['expense']
                })
            df_yearly = pd.DataFrame(yearly_data)
            total_year_income = df_yearly['Thu nhập'].sum()
            total_year_expense = df_yearly['Chi tiêu'].sum()
            total_year_balance = total_year_income - total_year_expense

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div style='background:white; padding:24px; border-radius:16px; 
                            box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:5px solid {COLOR_THU_MAIN};'>
                    <div style='color:#666; font-size:0.9rem;'>💵 Tổng thu năm</div>
                    <div style='font-size:1.8rem; font-weight:bold; color:{COLOR_THU_MAIN}; margin-top:8px;'>
                        {format_vnd(total_year_income)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style='background:white; padding:24px; border-radius:16px; 
                            box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:5px solid {COLOR_CHI_MAIN};'>
                    <div style='color:#666; font-size:0.9rem;'>💸 Tổng chi năm</div>
                    <div style='font-size:1.8rem; font-weight:bold; color:{COLOR_CHI_MAIN}; margin-top:8px;'>
                        {format_vnd(total_year_expense)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                du_color = COLOR_DU if total_year_balance >= 0 else COLOR_CHI_MAIN
                st.markdown(f"""
                <div style='background:white; padding:24px; border-radius:16px; 
                            box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:5px solid {du_color};'>
                    <div style='color:#666; font-size:0.9rem;'>📊 Số dư năm</div>
                    <div style='font-size:1.8rem; font-weight:bold; color:{du_color}; margin-top:8px;'>
                        {format_vnd(total_year_balance)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_yearly['Tháng'], y=df_yearly['Thu nhập'],
                                 name='Thu nhập', marker_color=COLOR_THU_MAIN,
                                 hovertemplate='<b>Tháng %{x}</b><br>Thu nhập: %{y:,.0f} đ<extra></extra>'))
            fig.add_trace(go.Bar(x=df_yearly['Tháng'], y=df_yearly['Chi tiêu'],
                                 name='Chi tiêu', marker_color=COLOR_CHI_MAIN,
                                 hovertemplate='<b>Tháng %{x}</b><br>Chi tiêu: %{y:,.0f} đ<extra></extra>'))
            fig.update_layout(title=f'So sánh thu nhập và chi tiêu năm {report_year}',
                              xaxis_title='Tháng', yaxis_title='Số tiền (VNĐ)', barmode='group',
                              hovermode='x unified',
                              paper_bgcolor='rgba(0,0,0,0)',
                              hoverlabel=dict(bgcolor='#FFF8E1', bordercolor=COLOR_CHI_MAIN))
            fig.update_xaxes(showspikes=True, spikecolor="#cccccc")
            fig.update_yaxes(showspikes=True, spikecolor="#cccccc")
            st.plotly_chart(fig, use_container_width=True)

            df_display = df_yearly.copy()
            df_display['Thu nhập'] = df_display['Thu nhập'].apply(format_vnd)
            df_display['Chi tiêu'] = df_display['Chi tiêu'].apply(format_vnd)
            df_display['Số dư'] = df_display['Số dư'].apply(format_vnd)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Xuất dữ liệu")
        col1, col2 = st.columns(2)
        with col1:
            export_start = st.date_input("Từ ngày", value=datetime(datetime.now().year, 1, 1), key="exp_start")
        with col2:
            export_end = st.date_input("Đến ngày", value=datetime.now(), key="exp_end")
        transactions = get_transactions(user_id,
                                        start_date=export_start.strftime('%Y-%m-%d'),
                                        end_date=export_end.strftime('%Y-%m-%d'))
        if transactions:
            df = pd.DataFrame(transactions)
            df['type'] = df['type'].map({'expense': 'Chi tiêu', 'income': 'Thu nhập'})
            df = df[['date', 'type', 'category', 'amount', 'note', 'created_at']]
            df.columns = ['Ngày', 'Loại', 'Danh mục', 'Số tiền', 'Ghi chú', 'Thời gian tạo']
            st.subheader("Xem trước dữ liệu")
            st.dataframe(df.head(20), use_container_width=True, hide_index=True)
            st.caption(f"Tổng cộng: {len(df)} bản ghi")
            col1, col2 = st.columns(2)
            with col1:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Giao dịch')
                    summary_data = {
                        'Chỉ tiêu': ['Tổng thu nhập', 'Tổng chi tiêu', 'Số dư'],
                        'Giá trị': [
                            df[df['Loại'] == 'Thu nhập']['Số tiền'].sum(),
                            df[df['Loại'] == 'Chi tiêu']['Số tiền'].sum(),
                            df[df['Loại'] == 'Thu nhập']['Số tiền'].sum() -
                            df[df['Loại'] == 'Chi tiêu']['Số tiền'].sum()
                        ]
                    }
                    pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Tổng hợp')
                buffer.seek(0)
                st.download_button(
                    label="📥 Tải file Excel (.xlsx)",
                    data=buffer,
                    file_name=f"baocao_{export_start}_{export_end}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with col2:
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Tải file CSV",
                    data=csv,
                    file_name=f"giaodich_{export_start}_{export_end}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("Không có dữ liệu trong khoảng thời gian này.")

    with tab3:
        st.subheader("🎯 Quản lý ngân sách")
        current_month = datetime.now().strftime('%Y-%m')
        expense_cats = get_user_categories(user_id, 'expense')
        with st.expander("➕ Đặt/Sửa ngân sách"):
            cat_names = [c['name'] for c in expense_cats]
            budget_cat = st.selectbox("Danh mục", cat_names, key="budget_cat")
            budget_amount = money_input("Số tiền ngân sách/tháng", min_value=0, step=100000, key="budget_amt")
            if st.button("💾 Lưu ngân sách", key="save_budget"):
                if set_budget(user_id, budget_cat, budget_amount, current_month):
                    st.success("Đã lưu ngân sách!")
                    st.rerun()

        budgets = get_budgets(user_id, current_month)
        if budgets:
            st.subheader(f"Tiến độ ngân sách tháng {current_month}")
            date_start = f"{current_month}-01"
            next_month = datetime.now().replace(day=28) + timedelta(days=4)
            date_end = next_month.replace(day=1).strftime('%Y-%m-%d')
            for budget in budgets:
                trans = get_transactions(user_id, trans_type='expense', category=budget['category'],
                                         start_date=date_start, end_date=date_end)
                spent = sum(t['amount'] for t in trans)
                remaining = budget['amount'] - spent
                pct_used = (spent / budget['amount'] * 100) if budget['amount'] > 0 else 0
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{budget['category']}**")
                    if pct_used > 100:
                        st.error(f"⚠️ Đã vượt ngân sách! Dùng {format_vnd(spent)} / {format_vnd(budget['amount'])}")
                        st.progress(1.0)
                    elif pct_used > 80:
                        st.warning(f"⚡ Sắp hết ngân sách! Dùng {format_vnd(spent)} / {format_vnd(budget['amount'])} ({pct_used:.1f}%)")
                        st.progress(pct_used / 100)
                    else:
                        st.success(f"✅ Dùng {format_vnd(spent)} / {format_vnd(budget['amount'])} ({pct_used:.1f}%)")
                        st.progress(pct_used / 100)
                with col2:
                    st.metric("Còn lại", format_vnd(remaining))
                with col3:
                    st.metric("Đã dùng", f"{pct_used:.1f}%")
                st.divider()
        else:
            st.info("Chưa đặt ngân sách nào. Hãy đặt ngân sách để kiểm soát chi tiêu!")

    with tab4:
        st.subheader("🔔 Nhắc nhở thanh toán")
        with st.expander("➕ Thêm nhắc nhở mới"):
            rem_title = st.text_input("Tiêu đề", placeholder="Ví dụ: Trả tiền điện, đóng học phí...", key="rem_title")
            rem_amount = money_input("Số tiền ước tính (VNĐ)", min_value=0, step=10000, key="rem_amt")
            rem_date = st.date_input("Ngày đến hạn", min_value=datetime.now(), key="rem_dt")
            rem_recurring = st.selectbox("Lặp lại", ["Không lặp", "Hàng tháng", "Hàng quý", "Hàng năm"], key="rem_rec")
            rem_note = st.text_area("Ghi chú", height=60, key="rem_nt")
            recurring_map = {"Không lặp": "none", "Hàng tháng": "monthly",
                             "Hàng quý": "quarterly", "Hàng năm": "yearly"}
            if st.button("💾 Lưu nhắc nhở", key="save_rem"):
                if not rem_title.strip():
                    st.error("Vui lòng nhập tiêu đề!")
                else:
                    if add_reminder(user_id, rem_title, rem_amount,
                                    rem_date.strftime('%Y-%m-%d'),
                                    recurring_map[rem_recurring], rem_note):
                        st.success("Đã thêm nhắc nhở!")
                        st.rerun()
                    else:
                        st.error("Lỗi!")

        reminders = get_reminders(user_id)
        if reminders:
            today = datetime.now().date()
            for rem in reminders:
                due_date = datetime.strptime(rem['due_date'], '%Y-%m-%d').date()
                days_left = (due_date - today).days
                if rem['is_paid']:
                    status = "✅ Đã thanh toán"
                elif days_left < 0:
                    status = f"🔴 Quá hạn {abs(days_left)} ngày"
                elif days_left == 0:
                    status = "🟡 Hôm nay đến hạn"
                elif days_left <= 7:
                    status = f"🟠 Còn {days_left} ngày"
                else:
                    status = f"🟢 Còn {days_left} ngày"
                with st.expander(f"{rem['title']} - {status}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Số tiền:** {format_vnd(rem['amount']) if rem['amount'] else 'Chưa xác định'}")
                        st.write(f"**Ngày đến hạn:** {rem['due_date']}")
                        recurring_text = {"none": "Không lặp", "monthly": "Hàng tháng",
                                          "quarterly": "Hàng quý", "yearly": "Hàng năm"}
                        st.write(f"**Lặp lại:** {recurring_text.get(rem['recurring'], 'Không lặp')}")
                    with col2:
                        if rem['note']:
                            st.write(f"**Ghi chú:** {rem['note']}")
                        st.write(f"**Trạng thái:** {status}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if not rem['is_paid']:
                            if st.button("✅ Đánh dấu đã thanh toán", key=f"paid_{rem['id']}"):
                                if mark_reminder_paid(rem['id'], user_id):
                                    st.success("Đã cập nhật!")
                                    st.rerun()
                    with col_b:
                        if st.button("🗑️ Xóa", key=f"del_rem_{rem['id']}"):
                            if delete_reminder(rem['id'], user_id):
                                st.success("Đã xóa!")
                                st.rerun()
        else:
            st.info("Chưa có nhắc nhở nào.")

def show_categories_page():
    st.header("📁 Quản lý danh mục")
    user_id = st.session_state['user']['id']
    tab1, tab2 = st.tabs(["💸 Danh mục chi tiêu", "💵 Danh mục thu nhập"])
    for tab, cat_type, tab_title in [(tab1, 'expense', 'Chi tiêu'), (tab2, 'income', 'Thu nhập')]:
        with tab:
            st.subheader(f"Danh mục {tab_title}")
            with st.expander(f"➕ Thêm danh mục {tab_title.lower()} mới"):
                new_name = st.text_input("Tên danh mục", key=f"new_{cat_type}")
                new_icon = st.text_input("Icon (emoji)", value="📦", key=f"icon_{cat_type}")
                if st.button(f"💾 Thêm danh mục {tab_title.lower()}", key=f"add_{cat_type}"):
                    if not new_name.strip():
                        st.error("Vui lòng nhập tên!")
                    else:
                        success, msg = add_category(user_id, new_name, cat_type, new_icon)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            categories = get_user_categories(user_id, cat_type)
            if categories:
                for cat in categories:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.write(f"### {cat['icon']}")
                    with col2:
                        st.write(f"**{cat['name']}**")
                    with col3:
                        if st.button("🗑️", key=f"del_cat_{cat['id']}"):
                            if delete_category(cat['id'], user_id):
                                st.success("Đã xóa!")
                                st.rerun()
            else:
                st.info("Chưa có danh mục nào.")

def main():
    init_database()
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    if not st.session_state['user']:
        remembered_user = check_login_token()
        if remembered_user:
            st.session_state['user'] = remembered_user

    st.markdown("""
        <style>
        .stApp { background: linear-gradient(135deg, #fffbeb 0%, #fef9c3 20%, #f0fdf4 60%, #ecfccb 100%); }
        .main .block-container { max-width: 1200px; padding-top: 2rem; padding-bottom: 2rem; }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #84cc16 0%, #a3e635 40%, #d9f99d 100%); width: 280px !important; }
        section[data-testid="stSidebar"] > div { width: 280px !important; }
        section[data-testid="stSidebar"] .stMarkdown p { color: #1a2e05 !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 0.5rem 0; }
        section[data-testid="stSidebar"] label { color: #1a2e05 !important; font-size: 1rem !important; font-weight: 600 !important; }
        section[data-testid="stSidebar"] .stRadio > div { gap: 0.5rem; }
        section[data-testid="stSidebar"] .stRadio label { padding: 0.6rem 0.75rem; border-radius: 0.75rem; transition: all 0.2s; width: 100%; }
        section[data-testid="stSidebar"] .stRadio label:hover { background-color: rgba(74, 124, 15, 0.2); transform: translateX(4px); }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #1a2e05 !important; font-size: 1rem !important; }
        section[data-testid="stSidebar"] .stButton > button { width: 100%; background: linear-gradient(135deg, #dc2626, #b91c1c); color: white; border: none; padding: 0.6rem 1rem; font-weight: 600; font-size: 1rem; border-radius: 0.75rem; transition: all 0.3s; margin-top: 1rem; box-shadow: 0 2px 8px rgba(220, 38, 38, 0.3); }
        section[data-testid="stSidebar"] .stButton > button:hover { background: linear-gradient(135deg, #b91c1c, #991b1b); box-shadow: 0 4px 16px rgba(220, 38, 38, 0.5); transform: translateY(-2px); }
        section[data-testid="stSidebar"] hr { border-color: rgba(74, 124, 15, 0.3); margin: 1rem 0; }
        h1 { color: #4d7c0f; font-size: 2.2rem !important; font-weight: 800 !important; margin-bottom: 1.5rem !important; padding-bottom: 0.5rem; border-bottom: 3px solid #84cc16; display: inline-block; }
        h2 { color: #4d7c0f; font-size: 1.6rem !important; font-weight: 700 !important; margin-top: 2rem !important; margin-bottom: 1rem !important; }
        h3 { color: #365314; font-size: 1.25rem !important; font-weight: 600 !important; }
        [data-testid="stMetric"] { background: white; padding: 1.25rem 1.5rem; border-radius: 1rem; box-shadow: 0 4px 12px rgba(77, 124, 15, 0.08); border: 1px solid #ecfccb; transition: transform 0.3s, box-shadow 0.3s; }
        [data-testid="stMetric"]:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(77, 124, 15, 0.15); }
        [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #78716c !important; font-weight: 500; }
        [data-testid="stMetricValue"] { font-size: 1.75rem !important; font-weight: 700 !important; color: #4d7c0f; }
        .stButton > button { border-radius: 0.75rem; font-weight: 600; padding: 0.5rem 1.25rem; transition: all 0.2s; background: linear-gradient(135deg, #84cc16, #65a30d); color: white; border: none; }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(132, 204, 22, 0.4); background: linear-gradient(135deg, #65a30d, #4d7c0f); }
        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; background: white; padding: 0.5rem; border-radius: 1rem; box-shadow: 0 2px 8px rgba(77, 124, 15, 0.08); margin-bottom: 1.5rem; }
        .stTabs [data-baseweb="tab"] { border-radius: 0.75rem; padding: 0.5rem 1rem; font-weight: 600; transition: all 0.2s; }
        .stTabs [data-baseweb="tab"]:hover { background: #ecfccb; }
        .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #84cc16, #65a30d) !important; color: white !important; box-shadow: 0 2px 8px rgba(132, 204, 22, 0.4); }
        [data-testid="stDataFrame"] { background: white; border-radius: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow: hidden; }
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > div, .stDateInput > div > div > input { border-radius: 0.5rem; border: 2px solid #e2e8f0; transition: border-color 0.2s, box-shadow 0.2s; }
        .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus, .stSelectbox > div > div > div:focus, .stDateInput > div > div > input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
        .streamlit-expanderHeader { background: white; border-radius: 0.5rem; font-weight: 600; }
        .streamlit-expanderContent { background: white; border-radius: 0 0 0.5rem 0.5rem; }
        .js-plotly-plot { background: white; border-radius: 0.75rem; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .stSelectbox > label, .stDateInput > label, .stTextInput > label, .stNumberInput > label { font-weight: 600; color: #334155; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.25rem; margin-bottom: 2rem; }
        .stat-card { background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06); border: 1px solid rgba(15, 23, 42, 0.06); transition: all 0.3s ease; position: relative; overflow: hidden; }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; }
        .stat-card:hover { transform: translateY(-4px); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.1); }
        .stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; margin-bottom: 0.75rem; }
        .stat-label { color: #64748b; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.25rem; }
        .stat-value { color: #0f172a; font-size: 1.5rem; font-weight: 700; line-height: 1.3; margin-bottom: 0.5rem; }
        .stat-trend { font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 20px; display: inline-block; }
        .stat-trend.up { background: rgba(0, 180, 42, 0.12); color: #00B42A; }
        .stat-trend.down { background: rgba(245, 63, 63, 0.1); color: #F53F3F; }
        .stat-income::before { background: linear-gradient(90deg, #00B42A, #52D96A); }
        .stat-expense::before { background: linear-gradient(90deg, #F53F3F, #FF6B6B); }
        .stat-balance::before { background: linear-gradient(90deg, #1565C0, #64B5F6); }
        .stat-loss::before { background: linear-gradient(90deg, #F53F3F, #FF6B6B); }
        .stat-savings::before { background: linear-gradient(90deg, #00B42A, #52D96A); }
        .stat-income .stat-icon { background: linear-gradient(135deg, #E8F5E9, #C8E6C9) !important; }
        .stat-expense .stat-icon { background: linear-gradient(135deg, #FFEBEE, #FFCDD2) !important; }
        .stat-balance .stat-icon { background: linear-gradient(135deg, #E3F2FD, #BBDEFB) !important; }
        .stat-loss .stat-icon { background: linear-gradient(135deg, #FFEBEE, #FFCDD2) !important; }
        .stat-savings .stat-icon { background: linear-gradient(135deg, #E8F5E9, #C8E6C9) !important; }
        .saving-item { background: white; border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; border: 1px solid rgba(15, 23, 42, 0.06); }
        .saving-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .saving-name { font-weight: 600; color: #0f172a; font-size: 0.875rem; }
        .saving-pct { font-weight: 700; color: #00B42A; font-size: 0.875rem; }
        .progress-bar-custom { height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-bottom: 0.5rem; }
        .progress-fill-custom { height: 100%; background: linear-gradient(90deg, #00B42A, #52D96A); border-radius: 4px; transition: width 0.5s ease; }
        .saving-amount { font-size: 0.75rem; color: #64748b; }
        .dashboard-grid [data-testid="stMetric"] { display: none; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        @media (max-width: 768px) { .dashboard-grid { grid-template-columns: repeat(2, 1fr); } }

        div[data-testid="stRadio"] div[role="radiogroup"] > label:first-child div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stRadio"] div[role="radiogroup"] > label:first-child p {
            color: #F53F3F !important;
            font-weight: 700 !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:last-child div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stRadio"] div[role="radiogroup"] > label:last-child p {
            color: #00B42A !important;
            font-weight: 700 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state['user']:
        show_auth_page()
        return

    user = st.session_state['user']

    with st.sidebar:
        st.markdown(f"### 👤 Xin chào, **{user['full_name']}**")
        st.markdown("---")
        menu = st.radio(
            "📋 Menu chính",
            ["🏠 Tổng quan", "💰 Giao dịch hàng ngày", "🏦 Quản lý tiết kiệm",
             "📈 Quản lý đầu tư", "📊 Báo cáo & Xuất dữ liệu",
             "📁 Quản lý danh mục"],
            key="main_menu"
        )
        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state['user'] = None
            delete_login_token()
            st.rerun()

    if menu == "🏠 Tổng quan":
        show_dashboard()
    elif menu == "💰 Giao dịch hàng ngày":
        show_transactions_page()
    elif menu == "🏦 Quản lý tiết kiệm":
        show_savings_page()
    elif menu == "📈 Quản lý đầu tư":
        show_investments_page()
    elif menu == "📊 Báo cáo & Xuất dữ liệu":
        show_reports_page()
    elif menu == "📁 Quản lý danh mục":
        show_categories_page()

if __name__ == "__main__":
    main()
