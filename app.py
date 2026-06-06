import re
import json
import math
import os  # ← これを追加

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# サーバー上でもデータベースが迷子にならないための絶対パス指定
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'trpg.db')
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
    
    # 立ち絵URL（通常・笑顔・狂気など）と技能データ
    image_normal = db.Column(db.String(500), default="")
    image_smile = db.Column(db.String(500), default="")
    image_insane = db.Column(db.String(500), default="")
    insanity_state = db.Column(db.String(200), default="正常")
    skills_json = db.Column(db.Text, default="{}")
    
    # 探索者メモ欄
    memo = db.Column(db.Text)

# アプリ起動時にデータベースを作成
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    invs = Investigator.query.all()
    return render_template('index.html', invs=invs)

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

def get_base_skills(dex_val, edu_val):
    return {
        "医学": 5, "言いくるめ": 5, "運転（自動車など）": 20, "応急手当": 30, "オカルト": 5,
        "重機械操作": 1, "化学": 1, "鍵開け": 1, "隠す": 15, "隠れる": 10, "機械修理": 20,
        "聞き耳": 25, "キック": 25, "クトゥルフ神話": 0, "組み付き": 25, "芸術（任意）": 5,
        "経理": 10, "拳銃": 20, "考古学": 1, "こぶし（パンチ）": 50, "コンピューター": 1,
        "サブマシンガン": 15, "写真術": 10, "重火器": 15, "乗馬": 5, "ショットガン": 30,
        "信用": 15, "心理学": 5, "人類学": 1, "水泳": 25, "製作（任意）": 5, "精神分析": 1,
        "生物学": 1, "説得": 15, "操縦（任意）": 1, "地質学": 1, "跳躍": 25, "追跡": 10,
        "電気修理": 10, "電子工学": 1, "天文学": 1, "投擲": 25, "頭突き": 10, "登攀": 40,
        "図書館": 25, "ナビゲート": 10, "値切り": 5, "博物学": 10, "物理学": 1, "変装": 1,
        "法律": 5, "星の配列": 1, "ほかの言語（任意）": 1, "母国語": edu_val * 5,
        "マーシャルアーツ": 1, "マシンガン": 15, "目星": 25, "薬学": 1,
        "ライフル": 25, "歴史": 20, "回避": dex_val * 2
    }

@app.route('/import', methods=['GET', 'POST'])
def import_text():
    if request.method == 'POST':
        raw_text = request.form['raw_text']
        
        # 基礎ステータス抽出用の関数
        def get_stat(stat_name, default=0):
            match = re.search(fr'{stat_name}[:：]\s*(\d+)', raw_text)
            return int(match.group(1)) if match else default

        name_match = re.search(r'^(.+?)\s*\(', raw_text)
        name = name_match.group(1).strip() if name_match else "名無し"
        
        age_match = re.search(r'\((\d+)歳\)', raw_text)
        age = age_match.group(1) if age_match else ""

        occ_match = re.search(r'所属：([^\n]+)', raw_text)
        occupation = occ_match.group(1).replace(' 男', '').replace(' 女', '').strip() if occ_match else ""

        # 基礎ステータス
        str_val = get_stat('STR')
        con_val = get_stat('CON')
        pow_val = get_stat('POW')
        dex_val = get_stat('DEX')
        app_val = get_stat('APP')
        siz_val = get_stat('SIZ')
        int_val = get_stat('INT')
        edu_val = get_stat('EDU')

        # 派生ステータス
        hp_val = get_stat('耐久力', default=math.ceil((con_val + siz_val) / 2))
        mp_val = get_stat('マジック・ポイント', default=pow_val)
        san_val = get_stat('正気度', default=pow_val * 5)
        idea_val = get_stat('アイデア', default=int_val * 5)
        know_val = get_stat('知識', default=edu_val * 5)
        luck_val = get_stat('幸運', default=pow_val * 5)

        # ダメージボーナス
        db_match = re.search(r'ダメージ・ボーナス[:：]\s*([+-]?\w+)', raw_text)
        if db_match:
            db_val = db_match.group(1)
        else:
            str_siz = str_val + siz_val
            db_val = "0"
            if 2 <= str_siz <= 12: db_val = "-1D6"
            elif 13 <= str_siz <= 16: db_val = "-1D4"
            elif 17 <= str_siz <= 24: db_val = "+0"
            elif 25 <= str_siz <= 32: db_val = "+1D4"
            elif 33 <= str_siz <= 40: db_val = "+1D6"

        # --- みくのリストを基にした全技能の初期値セット ---
        skills_dict = get_base_skills(dex_val, edu_val)

        # キャラエノのテキストから取得できたスキルで、初期値を「上書き」する
        skills_block_match = re.search(r'【技能】\s*\n(.*?)(?=-{5,})', raw_text, re.DOTALL)
        if skills_block_match:
            skills_text = skills_block_match.group(1)
            for line in skills_text.split('\n'):
                skill_match = re.search(r'(.*?)[:：]\s*(\d+)%', line)
                if skill_match:
                    s_name = skill_match.group(1).strip()
                    s_val = int(skill_match.group(2))
                    skills_dict[s_name] = s_val  # ここで上書き＆新規追加

        skills_json_str = json.dumps(skills_dict, ensure_ascii=False)

        # メモ欄のノイズカット（【武器】以降だけを綺麗に切り出す）
        memo_match = re.search(r'(【武器】.*)', raw_text, re.DOTALL)
        clean_memo = memo_match.group(1) if memo_match else raw_text

        new_inv = Investigator(
            name=name, occupation=occupation, age=age,
            str_val=str_val, con_val=con_val, pow_val=pow_val,
            dex_val=dex_val, app_val=app_val, siz_val=siz_val,
            int_val=int_val, edu_val=edu_val,
            hp_val=hp_val, mp_val=mp_val, san_val=san_val,
            idea_val=idea_val, know_val=know_val, luck_val=luck_val,
            db_val=db_val, skills_json=skills_json_str, memo=clean_memo
        )
        db.session.add(new_inv)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return render_template('import.html')

 # 画面側で「これは初期値か？」を判定できるように、基礎技能の値も渡してあるとこ
@app.route('/investigator/<int:id>')
def detail(id):
    inv = Investigator.query.get_or_404(id)
    skills = json.loads(inv.skills_json) if inv.skills_json else {}
    
    base_skills = get_base_skills(inv.dex_val, inv.edu_val) # ← これを追加
    
    combat_keywords = ['回避', 'キック', 'こぶし', '頭突き', '組み付き', 'マーシャルアーツ', '投擲', '拳銃', 'サブマシンガン', 'ショットガン', 'ライフル', 'マシンガン', '刀', '剣', '槍', '杖', '弓', 'ナイフ', 'ムチ', '斧', 'リボルバー', '火器']
    general_skills = {}
    combat_skills = {}
    
    for name, val in skills.items():
        if any(kw in name for kw in combat_keywords):
            combat_skills[name] = val
        else:
            general_skills[name] = val
            
    return render_template('detail.html', inv=inv, general_skills=general_skills, combat_skills=combat_skills, base_skills=base_skills)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    inv = Investigator.query.get_or_404(id)
    if request.method == 'POST':
        inv.name = request.form['name']
        inv.occupation = request.form['occupation']
        inv.age = request.form['age']
        
        inv.str_val = request.form['str_val']
        inv.con_val = request.form['con_val']
        inv.pow_val = request.form['pow_val']
        inv.dex_val = request.form['dex_val']
        inv.app_val = request.form['app_val']
        inv.siz_val = request.form['siz_val']
        inv.int_val = request.form['int_val']
        inv.edu_val = request.form['edu_val']
        
        inv.hp_val = request.form['hp_val']
        inv.mp_val = request.form['mp_val']
        inv.san_val = request.form['san_val']
        inv.idea_val = request.form['idea_val']
        inv.know_val = request.form['know_val']
        inv.luck_val = request.form['luck_val']
        inv.db_val = request.form['db_val']
        
        inv.image_normal = request.form.get('image_normal', '')
        inv.image_smile = request.form.get('image_smile', '')
        inv.image_insane = request.form.get('image_insane', '')
        inv.insanity_state = request.form.get('insanity_state', '正常')
        inv.memo = request.form['memo']

        # --- ここから技能の一括保存 ---
        updated_skills = {}
        for key, value in request.form.items():
            if key.startswith('skill_') and value != "":
                skill_name = key.replace('skill_', '')
                updated_skills[skill_name] = int(value)
        inv.skills_json = json.dumps(updated_skills, ensure_ascii=False)
        # ------------------------------------
        
        db.session.commit()
        return redirect(url_for('detail', id=inv.id))
    else:
        # 編集画面を開くときに技能リストを渡す
        skills = json.loads(inv.skills_json) if inv.skills_json else get_base_skills(inv.dex_val, inv.edu_val)
        return render_template('edit.html', inv=inv, skills=skills)

 # APIエンドポイント：探索者のHP/MP/SANを更新する（例: 戦闘中のリアルタイム更新用）
@app.route('/api/update_stat/<int:id>', methods=['POST'])
def update_stat(id):
    inv = Investigator.query.get_or_404(id)
    data = request.json
    if 'hp' in data:
        inv.hp_val = data['hp']
    if 'mp' in data:
        inv.mp_val = data['mp']
    if 'san' in data:
        inv.san_val = data['san']
    db.session.commit()
    return {"status": "success"}

@app.route('/party')
def party():
    # トップページから送信されたIDのリストを受け取る
    selected_ids = request.args.getlist('id')
    
    if selected_ids:
        # 選ばれたIDの探索者だけを取得
        invs = Investigator.query.filter(Investigator.id.in_(selected_ids)).all()
    else:
        # 何も選ばれずに直接アクセスされた場合は全員表示
        invs = Investigator.query.all()
    
    groups_def = {
        'あ行': ['医学', '言いくるめ', '運転', '応急手当', 'オカルト'],
        'か行': ['回避','化学', '鍵開け', '隠す', '隠れる', '機械修理', '聞き耳', 'クトゥルフ神話', '芸術', '経理','考古学','コンピューター'],
        'さ行': ['忍び歩き', '写真術', '重機械操作', '乗馬', '信用', '心理学', '人類学', '水泳', '製作', '精神分析', '生物学', '説得', '操縦'],
        'た行': ['地質学', '跳躍', '追跡', '電気修理', '電子工学', '天文学', '投擲','登攀', '図書館'],
        'な行': ['ナビゲート', '値切り'],
        'は行': ['博物学', '物理学', '変装', '法律', 'ほかの言語', '母国語', '星の配列'],
        'ま行': ['マーシャルアーツ', '目星'],
        'や行': ['薬学'],
        'ら行': ['歴史'],
        '戦闘技能': ['拳銃','サブマシンガン','ショットガン','マシンガン','ライフル','キック','組み','こぶし','頭突き','重火器'] 
    }
    
    party_data = []
    for inv in invs:
        skills_saved = json.loads(inv.skills_json) if inv.skills_json else {}
        base_skills = get_base_skills(inv.dex_val, inv.edu_val)
        
        all_skills = base_skills.copy()
        all_skills.update(skills_saved)
        
        # クトゥルフ神話技能からSAN値の上限を自動計算
        cthulhu = all_skills.get('クトゥルフ神話', 0)
        max_san = 99 - cthulhu
        
        grouped_skills = {k: {} for k in groups_def.keys()}
        
        for s_name, s_val in all_skills.items():
            placed = False
            for g_name, g_keywords in groups_def.items():
                if any(s_name.startswith(kw) for kw in g_keywords):
                    grouped_skills[g_name][s_name] = s_val
                    placed = True
                    break
            if not placed:
                if 'その他' not in grouped_skills:
                    grouped_skills['その他'] = {}
                grouped_skills['その他'][s_name] = s_val
                
        grouped_skills = {k: v for k, v in grouped_skills.items() if v}
        
        party_data.append({
            'inv': inv,
            'grouped_skills': grouped_skills,
            'max_san': max_san  # 計算結果を画面に渡す
        })
        
    return render_template('party.html', party_data=party_data)

if __name__ == '__main__':
    app.run(debug=True)