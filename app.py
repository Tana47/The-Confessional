import random
import string
import base64
from flask import Flask, request, render_template_string, session, redirect, url_for
from markupsafe import escape
from captcha.image import ImageCaptcha

app = Flask(__name__)
app.secret_key = 'super_secret_secure_key' 

# --- CONFIGURATION ---
VALID_SINS = {
    "LUST", "GLUTTONY", "GREED", "SLOTH", "WRATH", "ENVY", "PRIDE"
}

# --- HELPER FUNCTIONS ---
def generate_random_text(length=5):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')
    return ''.join(random.choices(chars, k=length))

# --- HTML TEMPLATES ---

# 1. CAPTCHA PAGE (Unchanged)
HTML_CAPTCHA = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        input { padding: 10px; margin-top: 10px; width: 200px; font-size: 16px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; margin-top: 10px; border-radius: 4px;}
        button:hover { background: #0056b3; }
        .error { color: red; margin-top: 10px; }
        .captcha-img { margin-bottom: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Human Verification</h2>
        <img src="data:image/png;base64,{{ captcha_image }}" class="captcha-img" alt="CAPTCHA">
        <form method="POST">
            <div>Type the characters above:</div>
            <input type="text" name="user_input" autocomplete="off" required>
            <br>
            <button type="submit">Verify</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <br>
        <a href="/">Refresh CAPTCHA</a>
    </div>
</body>
</html>
"""

# 2. SINS QUESTION PAGE (Widened and Styled)
HTML_QUESTION = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #222; color: #eee; }
        .container { 
            background: #333; 
            padding: 40px; 
            border-radius: 8px; 
            box-shadow: 0 10px 25px rgba(0,0,0,0.7); 
            text-align: center; 
            /* 1. INCREASED WIDTH TO FIT TEXT */
            width: 500px; 
            border: 1px solid #444;
        }
        input { 
            padding: 12px; 
            margin-top: 25px; 
            width: 85%; 
            font-size: 16px; 
            border: 1px solid #555; 
            border-radius: 4px; 
            background-color: #222; 
            color: white; 
            outline: none;
        }
        
        /* 2. STYLE THE PLACEHOLDER TO FIT */
        ::placeholder {
            font-size: 13px;
            font-style: italic;
            color: #777;
        }

        input:focus { border-color: #dc3545; }
        button { 
            padding: 12px 25px; 
            background: #dc3545; 
            color: white; 
            border: none; 
            cursor: pointer; 
            margin-top: 20px; 
            border-radius: 4px; 
            font-weight: bold; 
            letter-spacing: 1px;
            transition: background 0.2s;
        }
        button:hover { background: #b02a37; }
        
        .error-box { 
            color: #ff8787; 
            margin-top: 30px; 
            padding-top: 20px;
            border-top: 1px solid #555;
            font-family: 'Georgia', serif;
            font-size: 1.1em;
            line-height: 1.6;
            animation: fadeIn 0.5s ease-in-out;
        }
        
        .success { color: #51cf66; margin-top: 15px; font-size: 1.2em; }
        h2 { border-bottom: 2px solid #dc3545; padding-bottom: 10px; display: inline-block; margin-bottom: 5px;}
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        {% if not success %}
            <h2>The Second Step</h2>
            <p style="color: #bbb;">Which one of the seven deadly sins would you say you have the most in you?</p>
            <form method="POST">
                <input type="text" name="sin_input" placeholder="Pride, Lust, Envy, Sloth, Wrath, Greed, Gluttony" autocomplete="off" required>
                <br>
                <button type="submit">CONFESS</button>
            </form>
            
            {% if error %}
                <div class="error-box">
                    {{ error | safe }}
                </div>
            {% endif %}
            
        {% else %}
            <h2>Accepted</h2>
            <div class="success">You have chosen: <strong>{{ chosen_sin }}</strong>.</div>
            <p style="margin-top:20px; color: #888;">You may proceed.</p>
        {% endif %}
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def captcha_test():
    error = None

    if request.method == 'POST':
        user_input = request.form.get('user_input', '').upper().strip()
        
        if 'captcha_code' in session:
            if user_input == session['captcha_code']:
                session['is_human'] = True
                session.pop('captcha_code', None)
                return redirect(url_for('sins_question'))
            else:
                error = "Incorrect CAPTCHA. Please try again."
        else:
            error = "Session expired. Please refresh."

    image = ImageCaptcha(width=280, height=90)
    captcha_text = generate_random_text()
    session['captcha_code'] = captcha_text
    data = image.generate(captcha_text)
    captcha_base64 = base64.b64encode(data.getvalue()).decode('utf-8')

    return render_template_string(HTML_CAPTCHA, captcha_image=captcha_base64, error=error)

@app.route('/question', methods=['GET', 'POST'])
def sins_question():
    if not session.get('is_human'):
        return redirect(url_for('captcha_test'))

    error = None
    success = False
    chosen_sin = ""

    if request.method == 'POST':
        raw_input = request.form.get('sin_input', '').strip()
        sin_input = raw_input.upper()

        if sin_input in VALID_SINS:
            success = True
            chosen_sin = sin_input.title()
        else:
            safe_input = escape(raw_input)
            error = (
                f"<strong>'{safe_input}'</strong> is not one of the Seven.<br><br>"
                f"<em>Are you not human? Or do you simply think you are above the rest of the world?</em>"
            )

    return render_template_string(HTML_QUESTION, error=error, success=success, chosen_sin=chosen_sin)

if __name__ == "__main__":
    app.run(debug=True)