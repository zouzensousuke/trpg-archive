from flask import Flask, render_template, request, redirect, url_for
import re
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# データベースの設定（同じフォルダに trpg.db というファイルが作られる）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trpg.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 探索者のデータベースモデル（CoC6版仕様）
class Investigator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    occupation = db.Column(db.String(100))
    age = db.Column(db.String(20))
    
    # 基礎ステータス
    str_val = db.Column(db.Integer, default=0)
    con_val = db.Column(db.Integer, default=0)
    pow_val = db.Column(db.Integer, default=0)
    dex_val = db.Column(db.Integer, default=0)
    app_val = db.Column(db.Integer, default=0)
    siz_val = db.Column(db.Integer, default=0)
    int_val = db.Column(db.Integer, default=0)
    edu_val = db.Column(db.Integer, default=0)
    
    # 追加ステータス
    hp_val = db.Column(db.Integer, default=0)
    mp_val = db.Column(db.Integer, default=0)
    san_val = db.Column(db.Integer, default=0)
    idea_val = db.Column(db.Integer, default=0)
    know_val = db.Column(db.Integer, default=0)
    luck_val = db.Column(db.Integer, default=0)
    db_val = db.Column(db.String(20), default="0")
    
    # 探索者メモ欄
    memo = db.Column(db.Text)

# アプリ起動時にデータベースを作成
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # 登録されている全探索者を取得
    investigators = Investigator.query.all()
    return render_template('index.html', investigators=investigators)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        new_inv = Investigator(
            name=request.form['name'],
            occupation=request.form['occupation'],
            age=request.form['age'],
            str_val=request.form['str_val'],
            con_val=request.form['con_val'],
            pow_val=request.form['pow_val'],
            dex_val=request.form['dex_val'],
            app_val=request.form['app_val'],
            siz_val=request.form['siz_val'],
            int_val=request.form['int_val'],
            edu_val=request.form['edu_val'],
            hp_val=request.form['hp_val'],
            mp_val=request.form['mp_val'],
            san_val=request.form['san_val'],
            idea_val=request.form['idea_val'],
            know_val=request.form['know_val'],
            luck_val=request.form['luck_val'],
            db_val=request.form['db_val'],
            memo=request.form['memo']
        )
        db.session.add(new_inv)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return render_template('create.html')

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    # 指定されたIDの探索者を探して削除する
    inv = Investigator.query.get_or_404(id)
    db.session.delete(inv)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/import', methods=['GET', 'POST'])
def import_text():
    if request.method == 'POST':
        raw_text = request.form['raw_text']
        
        # 正規表現でテキストからデータを抽出する関数
        def get_stat(stat_name, default=0):
            # 例: "STR:13" や "耐久力：11" の数字部分を抜き出す
            match = re.search(fr'{stat_name}[:：]\s*(\d+)', raw_text)
            return int(match.group(1)) if match else default

        # 名前の抽出（最初の行から括弧の前までを名前とする）
        name_match = re.search(r'^(.+?)\s*\(', raw_text)
        name = name_match.group(1).strip() if name_match else "名無し"
        
        # 年齢の抽出
        age_match = re.search(r'\((\d+)歳\)', raw_text)
        age = age_match.group(1) if age_match else ""

        # 職業（所属）の抽出を追加
        occ_match = re.search(r'所属：([^\n]+)', raw_text)
        occupation = occ_match.group(1).replace(' 男', '').replace(' 女', '').strip() if occ_match else ""

        # ダメージボーナスの抽出（プラスマイナス記号付き）
        db_match = re.search(r'ダメージ・ボーナス[:：]\s*([+-]?\d+)', raw_text)
        db_val = db_match.group(1) if db_match else "0"

        # 抽出したデータで新しい探索者を作成
        new_inv = Investigator(
            name=name,
            occupation=occupation,
            age=age,
            str_val=get_stat('STR'),
            con_val=get_stat('CON'),
            pow_val=get_stat('POW'),
            dex_val=get_stat('DEX'),
            app_val=get_stat('APP'),
            siz_val=get_stat('SIZ'),
            int_val=get_stat('INT'),
            edu_val=get_stat('EDU'),
            hp_val=get_stat('耐久力'),
            mp_val=get_stat('マジック・ポイント'),
            san_val=get_stat('正気度'),
            idea_val=get_stat('アイデア'), # テキストになければ0になる
            know_val=get_stat('知識'),
            luck_val=get_stat('幸運'),
            db_val=db_val,
            memo=raw_text # コピペした全文はそのままメモ欄に残す
        )
        db.session.add(new_inv)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return render_template('import.html')

if __name__ == '__main__':
    app.run(debug=True)