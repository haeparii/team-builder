import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random
import copy
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io
import hashlib
import os
import string

# ──────────────────────────────────────────
# FIREBASE
# ──────────────────────────────────────────

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred_dict = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def get_db():
    return init_firebase()


# ──────────────────────────────────────────
# 상수
# ──────────────────────────────────────────

PERSONALITY_TYPES = {
    "리더형": [
        "나는 팀 활동에서 목표와 방향을 제시하는 역할을 자연스럽게 맡는다.",
        "팀원들이 갈등할 때 중재하거나 방향을 잡아주려 한다.",
        "팀의 전체적인 일정과 역할 분배를 내가 정리하고 싶다.",
        "새로운 아이디어를 먼저 제안하고 팀원들을 설득하는 편이다.",
        "팀이 어려운 상황일수록 내가 앞장서야 한다고 느낀다.",
    ],
    "분위기메이커형": [
        "팀 활동 중 분위기가 무거울 때 분위기를 풀어주는 역할을 한다.",
        "팀원들이 지칠 때 격려하거나 응원하는 말을 자주 한다.",
        "나는 모임이나 회의에서 유머나 가벼운 이야기로 활기를 불어넣는다.",
        "팀원들 사이의 친밀도를 높이기 위한 활동을 먼저 제안한다.",
        "팀의 사기를 높이는 것이 성과만큼 중요하다고 생각한다.",
    ],
    "아나운서형": [
        "팀의 결과물을 외부에 발표하거나 설명하는 역할이 편하다.",
        "복잡한 내용을 쉽게 정리해 전달하는 것을 잘한다.",
        "팀 회의에서 내용을 요약하거나 정리해 다시 공유하는 역할을 맡는다.",
        "발표 준비를 꼼꼼히 하고 청중 반응을 신경 쓰는 편이다.",
        "팀을 대표해서 다른 팀이나 외부와 소통하는 역할이 어렵지 않다.",
    ],
    "성실한팔로워형": [
        "리더가 정한 방향대로 성실하게 수행하는 것이 나의 강점이다.",
        "맡은 역할은 끝까지 책임지고 마무리한다.",
        "팀에서 세부적인 실행 업무를 꼼꼼히 챙기는 편이다.",
        "다른 사람이 놓친 부분을 발견하고 조용히 처리하는 편이다.",
        "화려하진 않더라도 팀의 기반을 다지는 역할이 좋다.",
    ],
    "경청형": [
        "팀원들의 이야기를 끝까지 들어주는 편이다.",
        "의견 충돌 시, 양쪽 입장을 모두 이해하려 노력한다.",
        "팀원이 고민을 나눌 때 조언보다 공감을 먼저 표현한다.",
        "회의에서 발언량이 적더라도 내용을 잘 파악하고 있다.",
        "팀원의 감정 상태를 잘 파악하고 배려하는 편이다.",
    ],
}

PERSONALITY_DESCRIPTIONS = {
    "리더형": "목표 설정과 방향 제시에 강점이 있으며, 팀을 이끄는 역할을 자연스럽게 맡습니다.",
    "분위기메이커형": "팀의 에너지와 사기를 높이는 역할을 하며, 팀워크를 즐겁게 만드는 사람입니다.",
    "아나운서형": "정보를 명확하게 전달하고 발표에 강점이 있으며, 팀의 대외 창구 역할을 합니다.",
    "성실한팔로워형": "맡은 일을 끝까지 책임지며, 팀의 실질적인 실행력을 담당하는 사람입니다.",
    "경청형": "팀원의 이야기를 잘 듣고 공감하며, 팀 내 갈등을 부드럽게 조율하는 사람입니다.",
}

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

CAREER_OPTIONS = [
    "경영/마케팅", "IT/개발", "디자인/예술", "교육",
    "의료/보건", "법률", "공학/기술", "연구/학문", "사회/복지", "미정",
]

MAX_SECTIONS = 5

WELCOME_MESSAGES = [
    "팀 프로젝트, 걱정 마세요! 설문 결과를 바탕으로 최적의 팀원들을 연결해 드릴게요.",
    "혼자라면 못 할 일도 팀이라면 가능합니다. 좋은 팀과 함께하세요!",
    "어떤 팀이 만들어질지 기대되지 않나요? 잠깐의 설문이 멋진 팀을 만들어 드립니다.",
    "좋은 팀은 다양한 강점이 모일 때 탄생합니다. 나만의 강점을 솔직하게 보여주세요!",
    "팀 구성은 저에게 맡겨두세요. 잘 맞는 팀원들과 함께할 수 있도록 도와드릴게요.",
]


# ──────────────────────────────────────────
# DB 헬퍼
# ──────────────────────────────────────────

def get_sections(professor_id=None):
    db = get_db()
    if professor_id:
        docs = db.collection("sections").where("professor_id", "==", professor_id).stream()
    else:
        docs = db.collection("sections").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]


def get_section(section_id):
    db = get_db()
    doc = db.collection("sections").document(section_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None


def get_students_in_section(section_id):
    db = get_db()
    docs = db.collection("students").where("section_id", "==", section_id).stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]


def get_student_by_email(email):
    db = get_db()
    docs = db.collection("students").where("email", "==", email.lower()).stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]


def get_teams(section_id):
    db = get_db()
    doc = db.collection("teams").document(section_id).get()
    return doc.to_dict() if doc.exists else None


# ──────────────────────────────────────────
# 교수 계정 헬퍼
# ──────────────────────────────────────────

def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return key.hex(), salt


def _verify_password(password, stored_hash, salt):
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return key.hex() == stored_hash


def get_professor_by_email(email):
    db = get_db()
    docs = db.collection("professors").where("email", "==", email.lower()).stream()
    results = [{**d.to_dict(), "id": d.id} for d in docs]
    return results[0] if results else None


def has_any_professor():
    db = get_db()
    docs = list(db.collection("professors").limit(1).stream())
    return len(docs) > 0


def create_professor(email, password, name, role="professor"):
    pw_hash, salt = _hash_password(password)
    db = get_db()
    ref = db.collection("professors").document()
    ref.set({
        "email": email.lower(),
        "name": name,
        "password_hash": pw_hash,
        "salt": salt,
        "role": role,
        "created_at": datetime.now().isoformat(),
    })
    return {**ref.get().to_dict(), "id": ref.id}


def get_invite_codes():
    db = get_db()
    docs = db.collection("invite_codes").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]


def create_invite_code():
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    db = get_db()
    ref = db.collection("invite_codes").document()
    ref.set({"code": code, "used": False, "used_by": "", "created_at": datetime.now().isoformat()})
    return code


def use_invite_code(code):
    db = get_db()
    docs = list(db.collection("invite_codes").where("code", "==", code).where("used", "==", False).stream())
    if not docs:
        return False
    docs[0].reference.update({"used": True})
    return True


def get_all_professors():
    db = get_db()
    docs = db.collection("professors").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]


def get_question_templates(professor_id):
    db = get_db()
    own = [{**d.to_dict(), "id": d.id} for d in
           db.collection("question_templates").where("professor_id", "==", professor_id).stream()]
    public = [{**d.to_dict(), "id": d.id} for d in
              db.collection("question_templates").where("is_public", "==", True).stream()]
    seen, result = set(), []
    for t in own + public:
        if t["id"] not in seen:
            seen.add(t["id"])
            result.append(t)
    return result


def save_question_template(professor_id, name, questions, is_public):
    db = get_db()
    ref = db.collection("question_templates").document()
    ref.set({
        "professor_id": professor_id,
        "name": name,
        "questions": questions,
        "is_public": is_public,
        "created_at": datetime.now().isoformat(),
    })
    return ref.id


# ──────────────────────────────────────────
# 엑셀 파싱
# ──────────────────────────────────────────

def parse_excel(file):
    try:
        raw = pd.read_excel(file, engine="openpyxl", header=None)
    except Exception:
        try:
            raw = pd.read_excel(file, engine="xlrd", header=None)
        except Exception as e:
            return None, f"파일을 읽을 수 없습니다: {e}"

    header_row = None
    for i, row in raw.iterrows():
        vals = [str(v) for v in row.values]
        if any("학번" in v for v in vals) and any("이름" in v for v in vals):
            header_row = i
            break

    if header_row is None:
        return None, "학번/이름 헤더 행을 찾을 수 없습니다."

    raw.columns = raw.iloc[header_row].astype(str).str.strip()
    df = raw.iloc[header_row + 1:].reset_index(drop=True)
    df = df.dropna(how="all")

    col_map = {}
    for col in df.columns:
        c = col.strip()
        if "E-MAIL" in c.upper() or "EMAIL" in c.upper() or "이메일" in c:
            col_map[col] = "email"
        elif "학번" in c:
            col_map[col] = "student_id"
        elif "이름" in c:
            col_map[col] = "name"
        elif "소속" in c or "학과" in c or "학부" in c:
            col_map[col] = "department"
        elif "학년" in c:
            col_map[col] = "grade"

    df = df.rename(columns=col_map)

    for req in ["email", "student_id", "name"]:
        if req not in df.columns:
            return None, f"'{req}' 컬럼을 찾을 수 없습니다."

    df = df[df["student_id"].notna()]
    df["student_id"] = df["student_id"].astype(str).str.strip().str.split(".").str[0]
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df["name"] = df["name"].astype(str).str.strip()
    if "department" not in df.columns:
        df["department"] = ""
    else:
        df["department"] = df["department"].astype(str).str.strip()

    keep = ["name", "student_id", "email", "department"]
    if "grade" in df.columns:
        keep.append("grade")

    return df[keep], None


# ──────────────────────────────────────────
# 팀 편성 알고리즘
# ──────────────────────────────────────────

def form_teams(students, num_teams, rules, team_sizes=None):
    shuffled = students.copy()
    random.shuffle(shuffled)
    teams = [[] for _ in range(num_teams)]

    if team_sizes and len(team_sizes) == num_teams and sum(team_sizes) == len(shuffled):
        max_sizes = team_sizes
    else:
        base_size = len(shuffled) // num_teams
        remainder = len(shuffled) % num_teams
        max_sizes = [base_size + (1 if i < remainder else 0) for i in range(num_teams)]

    for student in shuffled:
        best_team = None
        best_score = float("inf")

        for i, team in enumerate(teams):
            if len(team) >= max_sizes[i]:
                continue

            score = 0
            personalities = [m.get("personality_type", "") for m in team]
            genders = [m.get("gender", "") for m in team]
            mbtis = [m.get("mbti", "") for m in team]
            depts = [m.get("department", "") for m in team]

            p_rule = rules.get("personality", "mixed")
            if p_rule == "mixed":
                score += personalities.count(student.get("personality_type", "")) * 100
            elif p_rule == "same":
                score += len(set(personalities + [student.get("personality_type", "")]) - {""}) * 100

            g_rule = rules.get("gender", "balanced")
            sg = student.get("gender", "")
            if g_rule == "balanced":
                score += genders.count(sg) * 50
            elif g_rule == "same":
                score += len(set(genders + [sg]) - {""}) * 50

            m_rule = rules.get("mbti", "mixed")
            sm = student.get("mbti", "")
            if m_rule == "mixed":
                score += mbtis.count(sm) * 30
            elif m_rule == "same":
                score += len(set(mbtis + [sm]) - {""}) * 30

            ei_rule = rules.get("mbti_ei", "balanced")
            if ei_rule == "balanced" and sm:
                team_ei = [m.get("mbti", "")[0] for m in team if m.get("mbti")]
                score += team_ei.count(sm[0]) * 20

            d_rule = rules.get("department", "mixed")
            sd = student.get("department", "")
            if d_rule == "mixed":
                score += depts.count(sd) * 10
            elif d_rule == "same":
                score += len(set(depts + [sd]) - {""}) * 10

            c_rule = rules.get("career", "none")
            sc = student.get("career", "")
            careers = [m.get("career", "") for m in team]
            if c_rule == "mixed":
                score += careers.count(sc) * 10
            elif c_rule == "same":
                score += len(set(careers + [sc]) - {""}) * 10

            if score < best_score:
                best_score = score
                best_team = i

        if best_team is not None:
            teams[best_team].append(student)

    return teams


def serialize_teams(teams):
    result = []
    for team in teams:
        result.append([
            {
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "student_id": s.get("student_id", ""),
                "department": s.get("department", ""),
                "gender": s.get("gender", ""),
                "mbti": s.get("mbti", ""),
                "personality_type": s.get("personality_type", ""),
            }
            for s in team
        ])
    return result


def encode_teams(serialized):
    """Firestore는 중첩 배열을 허용하지 않으므로 team_0, team_1... 키로 분리 저장"""
    doc = {"num_teams": len(serialized)}
    for i, team in enumerate(serialized):
        doc[f"team_{i}"] = team
    return doc


def decode_teams(doc):
    """encode_teams로 저장된 문서에서 list-of-lists 복원"""
    if not doc:
        return []
    n = doc.get("num_teams", 0)
    return [doc.get(f"team_{i}", []) for i in range(n)]


# ──────────────────────────────────────────
# 이메일
# ──────────────────────────────────────────

def send_team_emails(teams, section_name, sender_email, sender_password):
    results = []
    for i, team in enumerate(teams):
        team_num = i + 1
        member_lines = "\n".join(
            f"  - {m['name']} ({m.get('department', '')}) {m.get('email', '')}"
            for m in team
        )
        for member in team:
            recipient = member.get("email", "")
            if not recipient or "@" not in recipient:
                continue
            try:
                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = recipient
                msg["Subject"] = f"[{section_name}] 팀 편성 결과 안내"
                body = (
                    f"안녕하세요, {member['name']}님!\n\n"
                    f"{section_name} 수업의 팀 편성 결과입니다.\n\n"
                    f"▶ 배정 팀: {team_num}팀\n\n"
                    f"▶ 팀원 명단:\n{member_lines}\n\n"
                    "좋은 팀 활동 되세요!"
                )
                msg.attach(MIMEText(body, "plain", "utf-8"))
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                results.append(f"✅ {recipient}")
            except Exception as e:
                results.append(f"❌ {recipient} — {e}")
    return results


# ──────────────────────────────────────────
# 페이지: 최초 슈퍼관리자 설정
# ──────────────────────────────────────────

def page_super_admin_setup():
    st.markdown("## 👥 팀 편성 시스템 — 초기 설정")
    st.info("처음 사용하시는군요! 슈퍼관리자 계정을 만들어주세요.")
    st.markdown("---")

    with st.form("setup_form"):
        name = st.text_input("이름")
        email = st.text_input("이메일")
        pw = st.text_input("비밀번호", type="password")
        pw2 = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("계정 생성", use_container_width=True, type="primary")

    if submitted:
        if not name or not email or not pw:
            st.error("모든 항목을 입력하세요.")
            return
        if pw != pw2:
            st.error("비밀번호가 일치하지 않습니다.")
            return
        if get_professor_by_email(email):
            st.error("이미 등록된 이메일입니다.")
            return
        prof = create_professor(email.strip(), pw, name.strip(), role="super_admin")
        st.session_state.update({"page": "admin_dashboard", "professor": prof})
        st.rerun()


# ──────────────────────────────────────────
# 페이지: 교수 회원가입
# ──────────────────────────────────────────

def page_professor_register():
    st.markdown("## 교수 회원가입")
    if st.button("← 로그인"):
        st.session_state["page"] = "login"
        st.rerun()
    st.markdown("---")

    with st.form("register_form"):
        invite = st.text_input("초대 코드")
        name = st.text_input("이름")
        email = st.text_input("이메일")
        pw = st.text_input("비밀번호", type="password")
        pw2 = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("가입하기", use_container_width=True, type="primary")

    if submitted:
        if not invite or not name or not email or not pw:
            st.error("모든 항목을 입력하세요.")
            return
        if pw != pw2:
            st.error("비밀번호가 일치하지 않습니다.")
            return
        if get_professor_by_email(email):
            st.error("이미 등록된 이메일입니다.")
            return
        if not use_invite_code(invite.strip().upper()):
            st.error("유효하지 않은 초대 코드입니다.")
            return
        prof = create_professor(email.strip(), pw, name.strip())
        st.session_state.update({"page": "admin_dashboard", "professor": prof})
        st.rerun()


# ──────────────────────────────────────────
# 페이지: 비밀번호 변경
# ──────────────────────────────────────────

def page_professor_change_password():
    prof = st.session_state.get("professor", {})
    st.markdown("## ✏️ 프로필 수정")
    if st.button("← 대시보드"):
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    st.markdown("---")

    st.markdown("#### 이름 변경")
    with st.form("change_name_form"):
        new_name = st.text_input("새 이름", value=prof.get("name", ""))
        if st.form_submit_button("이름 변경", use_container_width=True):
            if new_name.strip():
                get_db().collection("professors").document(prof["id"]).update({"name": new_name.strip()})
                updated = get_professor_by_email(prof["email"])
                st.session_state["professor"] = updated
                st.success("이름이 변경되었습니다.")
            else:
                st.error("이름을 입력하세요.")

    st.markdown("#### 비밀번호 변경")
    with st.form("change_pw_form"):
        current = st.text_input("현재 비밀번호", type="password")
        new_pw = st.text_input("새 비밀번호", type="password")
        new_pw2 = st.text_input("새 비밀번호 확인", type="password")
        submitted = st.form_submit_button("비밀번호 변경", use_container_width=True, type="primary")

    if submitted:
        if not _verify_password(current, prof["password_hash"], prof["salt"]):
            st.error("현재 비밀번호가 올바르지 않습니다.")
            return
        if new_pw != new_pw2:
            st.error("새 비밀번호가 일치하지 않습니다.")
            return
        if len(new_pw) < 6:
            st.error("비밀번호는 6자 이상이어야 합니다.")
            return
        pw_hash, salt = _hash_password(new_pw)
        get_db().collection("professors").document(prof["id"]).update({"password_hash": pw_hash, "salt": salt})
        updated = get_professor_by_email(prof["email"])
        st.session_state["professor"] = updated
        st.success("비밀번호가 변경되었습니다.")


# ──────────────────────────────────────────
# 페이지: 초대 코드 관리 (슈퍼관리자)
# ──────────────────────────────────────────

def page_super_admin_invite_codes():
    st.markdown("## 초대 코드 관리")
    if st.button("← 대시보드"):
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    st.markdown("---")

    if st.button("➕ 새 초대 코드 생성", type="primary"):
        code = create_invite_code()
        st.success(f"생성된 코드: **{code}**")

    st.markdown("---")
    codes = get_invite_codes()
    if not codes:
        st.info("생성된 초대 코드가 없습니다.")
        return

    df = pd.DataFrame([{
        "코드": c["code"],
        "상태": "사용됨" if c.get("used") else "미사용",
        "생성일": c.get("created_at", "")[:10],
    } for c in codes])
    st.dataframe(df, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────
# 페이지: 로그인
# ──────────────────────────────────────────

def page_login():
    # 교수 계정이 없으면 최초 설정 페이지로
    if not has_any_professor():
        st.session_state["page"] = "super_admin_setup"
        st.rerun()

    st.markdown("## 👥 팀 편성 시스템")
    st.markdown("---")

    mode = st.radio("로그인 유형", ["학생", "교수"], horizontal=True)

    if mode == "학생":
        with st.form("student_login"):
            email = st.text_input("이메일 (아이디)")
            student_id = st.text_input("학번 (비밀번호)", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)

        if submitted:
            if not email or not student_id:
                st.error("이메일과 학번을 입력하세요.")
                return
            matches = get_student_by_email(email.strip().lower())
            if not matches:
                st.error("등록되지 않은 이메일입니다.")
                return
            valid = [s for s in matches if str(s.get("student_id", "")) == str(student_id).strip()]
            if not valid:
                st.error("학번이 올바르지 않습니다.")
                return
            if len(valid) > 1:
                st.session_state.update({"page": "student_select_section", "student_matches": valid})
            else:
                st.session_state.update({"page": "student_main", "student": valid[0]})
            st.rerun()

    else:
        with st.form("professor_login"):
            email = st.text_input("이메일")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)

        if submitted:
            prof = get_professor_by_email(email.strip())
            if not prof or not _verify_password(password, prof["password_hash"], prof["salt"]):
                st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
            else:
                st.session_state.update({"page": "admin_dashboard", "professor": prof})
                st.rerun()

        st.markdown("---")
        st.caption("초대 코드가 있으신가요?")
        if st.button("회원가입", use_container_width=True):
            st.session_state["page"] = "professor_register"
            st.rerun()


# ──────────────────────────────────────────
# 페이지: 학생 — 수업 선택
# ──────────────────────────────────────────

def page_student_select_section():
    st.markdown("## 수업 선택")
    matches = st.session_state.get("student_matches", [])

    options = {}
    for s in matches:
        sec = get_section(s.get("section_id", ""))
        if sec:
            options[sec["name"]] = s

    if not options:
        st.error("수업 정보를 찾을 수 없습니다.")
        return

    st.write("동일 교수의 여러 수업에 등록되어 있습니다. 오늘 참여할 수업을 선택하세요.")
    selected = st.radio("수업 선택", list(options.keys()))
    if st.button("확인", use_container_width=True):
        st.session_state.update({"page": "student_main", "student": options[selected]})
        st.rerun()


# ──────────────────────────────────────────
# 페이지: 학생 메인 (설문 or 결과)
# ──────────────────────────────────────────

def page_student_main():
    student = st.session_state.get("student", {})
    section = get_section(student.get("section_id", ""))

    if not section:
        st.error("수업 정보를 찾을 수 없습니다.")
        return

    # 팀 공개된 경우 → 결과 페이지
    if section.get("teams_published", False):
        page_student_result(student, section)
        return

    # 설문 완료된 경우 → 대기 페이지
    if student.get("survey_completed", False):
        st.markdown(f"## {section['name']}")
        st.success("설문을 완료하셨습니다. 교수님이 팀을 편성하면 이 페이지에서 결과를 확인할 수 있습니다.")
        if st.button("로그아웃"):
            st.session_state.clear()
            st.rerun()
        return

    # 설문 마감된 경우 → 미완료 학생 접근 차단
    if section.get("survey_closed", False):
        st.markdown(f"## {section['name']}")
        st.warning("설문이 마감되었습니다. 교수님이 팀을 편성 중입니다.")
        if st.button("로그아웃"):
            st.session_state.clear()
            st.rerun()
        return

    # 설문 페이지
    page_student_survey(student, section)


def page_student_survey(student, section):
    SCORE_MAP = {"아니다": 0, "보통": 1, "그렇다": 2}
    LABELS = ["아니다", "보통", "그렇다"]
    PER_PAGE = 5

    # 질문 목록 구성
    custom_q = section.get("custom_questions")
    if custom_q:
        all_q = {pt: list(custom_q.get(pt, [])) for pt in PERSONALITY_TYPES}
    else:
        extra_q = section.get("extra_questions", {})
        all_q = {pt: PERSONALITY_TYPES[pt] + extra_q.get(pt, []) for pt in PERSONALITY_TYPES}
    questions_flat = [(pt, q) for pt, qs in all_q.items() for q in qs]

    # 세션 상태 초기화
    if "survey_page" not in st.session_state:
        st.session_state["survey_page"] = 0
    if "survey_answers" not in st.session_state:
        st.session_state["survey_answers"] = {}
    if "welcome_msg" not in st.session_state:
        st.session_state["welcome_msg"] = random.choice(WELCOME_MESSAGES)
    if "survey_seed" not in st.session_state:
        st.session_state["survey_seed"] = random.randint(0, 2 ** 32)

    # 세션 내 일관된 랜덤 순서 (매 세션마다 다르게)
    rng = random.Random(st.session_state["survey_seed"])
    rng.shuffle(questions_flat)

    total_pages = (len(questions_flat) + PER_PAGE - 1) // PER_PAGE

    page = st.session_state["survey_page"]
    start = page * PER_PAGE
    page_qs = questions_flat[start:start + PER_PAGE]

    # 환영 메시지 (첫 페이지에만)
    if page == 0:
        st.markdown(f"## 반갑습니다, {student.get('name', '')}님!")
        st.info(st.session_state["welcome_msg"])
        st.markdown("---")

    st.subheader(f"{section['name']} — 팀 편성 설문")

    # 진행 상태
    st.progress((page) / total_pages)
    st.caption(f"질문 {start + 1}–{min(start + PER_PAGE, len(questions_flat))} / {len(questions_flat)}")
    st.markdown("---")

    # 기본 정보 (첫 페이지에만)
    if page == 0:
        st.markdown("**기본 정보**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.radio("성별", ["남", "여"], horizontal=True, key="basic_gender")
        with col2:
            st.selectbox("MBTI", ["모름"] + MBTI_TYPES, key="basic_mbti")
        with col3:
            st.selectbox("희망진로", CAREER_OPTIONS, key="basic_career")
        st.markdown("---")

    # 질문 표시
    for i, (pt, q) in enumerate(page_qs):
        global_idx = start + i
        saved_score = st.session_state["survey_answers"].get(global_idx, {}).get("score", 1)
        st.markdown(f"<p style='font-size:17px; font-weight:600; margin-bottom:4px'>{q}</p>", unsafe_allow_html=True)
        st.radio("", LABELS, index=saved_score, horizontal=True, key=f"radio_{global_idx}", label_visibility="collapsed")
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    def save_current_page():
        for i, (pt, _) in enumerate(page_qs):
            global_idx = start + i
            val = st.session_state.get(f"radio_{global_idx}", "보통")
            st.session_state["survey_answers"][global_idx] = {"pt": pt, "score": SCORE_MAP[val]}

    col_prev, col_next = st.columns(2)

    if page > 0:
        if col_prev.button("← 이전", use_container_width=True):
            save_current_page()
            st.session_state["survey_page"] -= 1
            st.rerun()

    is_last = page >= total_pages - 1
    next_label = "제출하기" if is_last else "다음 →"
    if col_next.button(next_label, use_container_width=True, type="primary"):
        save_current_page()
        if not is_last:
            st.session_state["survey_page"] += 1
            st.rerun()
        else:
            scores = {pt: 0 for pt in PERSONALITY_TYPES}
            for ans in st.session_state["survey_answers"].values():
                scores[ans["pt"]] += ans["score"]

            personality = max(scores, key=scores.get)
            gender = st.session_state.get("basic_gender", "남")
            mbti = st.session_state.get("basic_mbti", "모름")
            career = st.session_state.get("basic_career", CAREER_OPTIONS[0])

            db = get_db()
            db.collection("students").document(student["id"]).update({
                "gender": gender,
                "mbti": "" if mbti == "모름" else mbti,
                "career": career,
                "personality_type": personality,
                "personality_scores": scores,
                "survey_completed": True,
                "survey_completed_at": datetime.now().isoformat(),
            })

            st.session_state["student"] = {
                **student,
                "gender": gender,
                "mbti": "" if mbti == "모름" else mbti,
                "career": career,
                "personality_type": personality,
                "personality_scores": scores,
                "survey_completed": True,
            }

            for key in ["survey_page", "survey_answers", "welcome_msg", "survey_seed"]:
                st.session_state.pop(key, None)

            st.session_state["page"] = "student_personality_result"
            st.rerun()


def page_student_personality_result():
    student = st.session_state.get("student", {})
    personality = student.get("personality_type", "")
    scores = student.get("personality_scores", {})

    st.markdown("## 설문 완료!")
    st.markdown("---")
    st.subheader(f"당신의 성향은 **{personality}** 입니다!")
    st.info(PERSONALITY_DESCRIPTIONS.get(personality, ""))

    st.markdown("#### 성향별 점수")
    bar_max = max(scores.values()) if scores else 1
    for pt, sc in sorted(scores.items(), key=lambda x: -x[1]):
        filled = round(sc / bar_max * 10) if bar_max else 0
        bar = "█" * filled + "░" * (10 - filled)
        st.write(f"**{pt}** `{bar}` {sc}점")

    st.markdown("---")
    st.success("팀 편성이 완료되면 다시 로그인하면 팀 결과를 확인할 수 있습니다.")
    if st.button("로그아웃"):
        st.session_state.clear()
        st.rerun()


def page_student_result(student, section):
    teams_data = get_teams(section["id"])
    if not teams_data or not teams_data.get("published", False):
        st.info("팀 결과가 아직 공개되지 않았습니다.")
        if st.button("로그아웃"):
            st.session_state.clear()
            st.rerun()
        return

    teams = decode_teams(teams_data)
    st.markdown(f"## {section['name']} — 팀 편성 결과")
    st.markdown("---")

    my_team_idx = None
    for i, team in enumerate(teams):
        if any(m.get("email") == student.get("email") for m in team):
            my_team_idx = i
            break

    if my_team_idx is not None:
        st.success(f"🎉 나의 팀: **{my_team_idx + 1}팀**")
        for m in teams[my_team_idx]:
            icon = "⭐ " if m.get("email") == student.get("email") else "• "
            st.write(f"{icon}**{m['name']}** ({m.get('department', '')})")
        st.markdown("---")

    st.subheader("전체 팀 구성")
    for i, team in enumerate(teams):
        label = f"{i+1}팀 ({len(team)}명)"
        with st.expander(label, expanded=(i == my_team_idx)):
            df = pd.DataFrame([{
                "이름": m["name"],
                "학과": m.get("department", ""),
            } for m in team])
            st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("로그아웃"):
        st.session_state.clear()
        st.rerun()


# ──────────────────────────────────────────
# 페이지: 관리자 대시보드
# ──────────────────────────────────────────

def page_admin_dashboard():
    prof = st.session_state.get("professor", {})
    is_super = prof.get("role") == "super_admin"

    # 헤더 배너
    role_badge = '<span style="background:#EDE9FE;color:#6D28D9;font-size:11px;font-weight:600;padding:2px 8px;border-radius:99px;margin-left:8px;">슈퍼관리자</span>' if is_super else ''
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%);
            border-radius:14px;padding:1.2rem 1.5rem 1rem;margin-bottom:1rem;">
  <div style="color:#C7D2FE;font-size:12px;font-weight:500;margin-bottom:2px;">팀 편성 시스템</div>
  <div style="color:#FFFFFF;font-size:1.15rem;font-weight:700;letter-spacing:-0.01em;">
    👥 {prof.get('name', '')}님의 대시보드{role_badge}
  </div>
</div>
""", unsafe_allow_html=True)

    # 버튼 툴바 — 4등분 행
    if is_super:
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("초대코드", use_container_width=True):
            st.session_state["show_invite"] = not st.session_state.get("show_invite", False)
            st.rerun()
        if b2.button("교수자 목록", use_container_width=True):
            st.session_state["page"] = "admin_professor_list"
            st.rerun()
        if b3.button("프로필", use_container_width=True):
            st.session_state["page"] = "professor_change_password"
            st.rerun()
        if b4.button("로그아웃", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    else:
        _, _, b3, b4 = st.columns(4)
        if b3.button("프로필", use_container_width=True):
            st.session_state["page"] = "professor_change_password"
            st.rerun()
        if b4.button("로그아웃", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # 초대 코드 인라인 패널 (슈퍼관리자)
    if is_super and st.session_state.get("show_invite"):
        with st.container(border=True):
            c_head, c_close = st.columns([4, 1])
            c_head.markdown("**🔑 초대 코드 관리**")
            if c_close.button("✕ 닫기", key="close_invite"):
                st.session_state["show_invite"] = False
                st.rerun()
            if st.button("➕ 새 코드 생성"):
                code = create_invite_code()
                st.success(f"생성된 코드: **`{code}`**")
            codes = get_invite_codes()
            if codes:
                for c in codes:
                    ci1, ci2, ci3, ci4 = st.columns([2, 2, 2, 1])
                    ci1.code(c["code"])
                    ci2.write("✅ 사용됨" if c.get("used") else "⏳ 미사용")
                    ci3.caption(c.get("created_at", "")[:10])
                    if not c.get("used"):
                        if ci4.button("🗑️", key=f"del_code_{c['id']}"):
                            get_db().collection("invite_codes").document(c["id"]).delete()
                            st.rerun()
            else:
                st.caption("생성된 코드가 없습니다.")

    st.markdown("---")

    # professor_id 없는 기존 분반을 슈퍼관리자에게 자동 연결
    if is_super:
        db = get_db()
        orphaned = [s for s in get_sections() if not s.get("professor_id")]
        for s in orphaned:
            db.collection("sections").document(s["id"]).update({"professor_id": prof.get("id", "")})

    sections = get_sections(professor_id=prof.get("id"))

    if len(sections) < MAX_SECTIONS:
        if st.button("➕ 새 분반 만들기", type="primary"):
            st.session_state["page"] = "admin_create_section"
            st.rerun()
    else:
        st.info(f"최대 {MAX_SECTIONS}개 분반까지 생성 가능합니다.")

    if not sections:
        st.info("등록된 분반이 없습니다.")
        return

    st.markdown("---")
    for sec in sections:
        students = get_students_in_section(sec["id"])
        total = len(students)
        done = sum(1 for s in students if s.get("survey_completed", False))
        published = sec.get("teams_published", False)

        closed = sec.get("survey_closed", False)
        survey_status = f"🔒 마감 {done}/{total}명" if closed else f"설문 {done}/{total}명"
        is_last = st.session_state.get("last_section") == sec["id"]
        with st.expander(
            f"📚 {sec['name']}  |  {survey_status}  |  {'✅ 공개됨' if published else '대기 중'}",
            expanded=is_last,
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("전체 학생", total)
            c2.metric("설문 완료", done)
            c3.metric("완료율", f"{int(done / total * 100) if total else 0}%")

            b1, b2, b3, b4 = st.columns(4)
            if b1.button("현황 보기", key=f"detail_{sec['id']}"):
                st.session_state.update({"page": "admin_section_detail", "cur_section": sec["id"], "last_section": sec["id"]})
                st.rerun()
            if b2.button("팀 편성", key=f"team_{sec['id']}"):
                st.session_state.update({"page": "admin_team_formation", "cur_section": sec["id"], "last_section": sec["id"]})
                st.rerun()
            if b3.button("설정 수정", key=f"edit_{sec['id']}"):
                st.session_state.update({"page": "admin_edit_section", "cur_section": sec["id"], "last_section": sec["id"]})
                st.rerun()
            if b4.button("분반 삭제", key=f"del_{sec['id']}"):
                st.session_state.update({"confirm_delete": sec["id"]})

    if "confirm_delete" in st.session_state:
        sec_id = st.session_state["confirm_delete"]
        sec = get_section(sec_id)
        st.warning(f"'{sec['name']}' 분반을 삭제하시겠습니까? 학생 데이터도 모두 삭제됩니다.")
        col_y, col_n = st.columns(2)
        if col_y.button("삭제 확인", type="primary"):
            db = get_db()
            for s in get_students_in_section(sec_id):
                db.collection("students").document(s["id"]).delete()
            db.collection("sections").document(sec_id).delete()
            teams_doc = db.collection("teams").document(sec_id).get()
            if teams_doc.exists:
                db.collection("teams").document(sec_id).delete()
            del st.session_state["confirm_delete"]
            st.rerun()
        if col_n.button("취소"):
            del st.session_state["confirm_delete"]
            st.rerun()


# ──────────────────────────────────────────
# 페이지: 교수자 목록 (슈퍼관리자 전용)
# ──────────────────────────────────────────

def page_admin_professor_list():
    st.markdown("## 교수자 목록")
    if st.button("← 대시보드"):
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    st.markdown("---")

    all_profs = get_all_professors()
    if not all_profs:
        st.info("등록된 교수자가 없습니다.")
        return

    st.caption(f"총 {len(all_profs)}명")
    st.markdown("")

    h1, h2, h3, h4 = st.columns([2, 3, 2, 2])
    h1.markdown("**이름**")
    h2.markdown("**이메일**")
    h3.markdown("**권한**")
    h4.markdown("**가입일**")
    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    for p in all_profs:
        p1, p2, p3, p4 = st.columns([2, 3, 2, 2])
        p1.write(p.get("name", "—"))
        p2.write(p.get("email", "—"))
        p3.write("슈퍼관리자" if p.get("role") == "super_admin" else "교수")
        p4.caption(p.get("created_at", "")[:10])


# ──────────────────────────────────────────
# 페이지: 분반 생성
# ──────────────────────────────────────────

RULE_OPTIONS = {
    "personality": {
        "mixed": "서로 다른 성향으로 구성",
        "same": "동일한 성향으로 구성",
    },
    "gender": {
        "balanced": "성별 균형 맞추기",
        "mixed": "혼합 (제한 없음)",
        "same": "동일 성별로 구성",
    },
    "mbti": {
        "mixed": "서로 다른 MBTI",
        "same": "동일한 MBTI",
        "none": "MBTI 고려 안 함",
    },
    "mbti_ei": {
        "balanced": "E/I 균형 맞추기",
        "mixed": "혼합",
        "none": "고려 안 함",
    },
    "department": {
        "mixed": "서로 다른 학과",
        "same": "동일 학과",
        "none": "학과 고려 안 함",
    },
    "career": {
        "mixed": "서로 다른 진로",
        "same": "동일 진로",
        "none": "진로 고려 안 함",
    },
}


def _render_question_editor():
    prof = st.session_state.get("professor", {})

    st.markdown("#### 설문 질문 설정")
    st.info(
        "현재 **25개 기본 질문**이 설문에서 성향이 드러나지 않도록 랜덤으로 섞여 제시됩니다. "
        "아래에서 질문을 삭제하거나 추가하고, 나만의 템플릿으로 저장할 수 있습니다."
    )

    questions = st.session_state.get("section_questions", {})
    total_q = sum(len(v) for v in questions.values())
    st.caption(f"현재 질문 수: {total_q}개")

    # 초기화 & 템플릿 불러오기
    c_reset, c_tpl = st.columns([1, 3])
    if c_reset.button("↺ 기본값 초기화", key="q_reset"):
        st.session_state["section_questions"] = {pt: list(qs) for pt, qs in PERSONALITY_TYPES.items()}
        st.rerun()

    templates = get_question_templates(prof.get("id", ""))
    tpl_key = f"q_tpl_select_{st.session_state.get('q_tpl_ver', 0)}"
    tpl_options = ["— 템플릿 선택 —"] + [
        t["name"] + (" [공개]" if t.get("is_public") else "") for t in templates
    ]
    chosen_tpl = c_tpl.selectbox("저장된 템플릿 불러오기", tpl_options, key=tpl_key, label_visibility="collapsed")
    if chosen_tpl != "— 템플릿 선택 —":
        idx = tpl_options.index(chosen_tpl) - 1
        tpl_q = templates[idx].get("questions", {})
        st.session_state["section_questions"] = {pt: list(tpl_q.get(pt, [])) for pt in PERSONALITY_TYPES}
        st.session_state["q_tpl_ver"] = st.session_state.get("q_tpl_ver", 0) + 1
        st.rerun()

    st.markdown("---")

    # 질문 목록 (성향별)
    for pt in PERSONALITY_TYPES.keys():
        qs = questions.get(pt, [])
        with st.expander(f"{pt}  ({len(qs)}개)", expanded=False):
            if not qs:
                st.caption("질문 없음")
            for i, q in enumerate(qs):
                c_q, c_del = st.columns([14, 1])
                c_q.write(q)
                if c_del.button("✕", key=f"q_del_{pt}_{i}", help="이 질문 삭제"):
                    st.session_state["section_questions"][pt] = [x for j, x in enumerate(qs) if j != i]
                    st.rerun()

    st.markdown("---")

    # 질문 추가
    st.markdown("**질문 추가**")
    c_new_pt, c_new_q, c_new_add = st.columns([2, 7, 1])
    new_pt = c_new_pt.selectbox("성향", list(PERSONALITY_TYPES.keys()), key="q_new_pt", label_visibility="collapsed")
    new_q_text = c_new_q.text_input("질문 내용", key="q_new_text", label_visibility="collapsed", placeholder="새 질문 내용을 입력하세요")
    if c_new_add.button("추가", key="q_new_add"):
        if new_q_text.strip():
            st.session_state["section_questions"].setdefault(new_pt, []).append(new_q_text.strip())
            st.rerun()
        else:
            st.warning("질문 내용을 입력하세요.")

    st.markdown("---")

    # 템플릿 저장
    st.markdown("**템플릿으로 저장**")
    c_tname, c_pub, c_save = st.columns([4, 3, 1])
    tpl_name_in = c_tname.text_input("이름", key="q_tpl_name_in", label_visibility="collapsed", placeholder="템플릿 이름")
    is_public = c_pub.checkbox("다른 교수자와 공유 (공개)", key="q_tpl_is_public")
    if c_save.button("저장", key="q_tpl_save"):
        if not tpl_name_in.strip():
            st.warning("템플릿 이름을 입력하세요.")
        else:
            save_question_template(
                prof.get("id", ""),
                tpl_name_in.strip(),
                st.session_state.get("section_questions", {}),
                is_public,
            )
            st.success(f"템플릿 '{tpl_name_in.strip()}'이 저장되었습니다.")


def page_admin_create_section():
    st.markdown("## 새 분반 만들기")
    if st.button("← 대시보드"):
        st.session_state.pop("section_questions", None)
        st.session_state.pop("q_tpl_ver", None)
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    st.markdown("---")

    if "section_questions" not in st.session_state:
        st.session_state["section_questions"] = {pt: list(qs) for pt, qs in PERSONALITY_TYPES.items()}

    with st.form("create_section"):
        section_name = st.text_input("분반 이름", placeholder="예: 인간학1 — 1분반")
        uploaded = st.file_uploader("학생 명단 엑셀 업로드", type=["xlsx", "xls"])

        st.markdown("#### 팀 구성 규칙")
        num_teams = st.number_input("팀 수", min_value=2, max_value=20, value=5)
        custom_sizes_input = st.text_input(
            "팀별 인원 수 (선택)",
            placeholder="예: 4,3,3 — 비워두면 자동 배분",
            help="팀 수만큼 쉼표로 구분해 입력하세요. 합계는 전체 학생 수와 일치해야 합니다.",
        )

        col1, col2 = st.columns(2)
        with col1:
            p_rule = st.selectbox("성향 구성", list(RULE_OPTIONS["personality"].values()))
            g_rule = st.selectbox("성별 구성", list(RULE_OPTIONS["gender"].values()))
            m_rule = st.selectbox("MBTI 구성", list(RULE_OPTIONS["mbti"].values()))
        with col2:
            ei_rule = st.selectbox("E/I 성향", list(RULE_OPTIONS["mbti_ei"].values()))
            d_rule = st.selectbox("학과 구성", list(RULE_OPTIONS["department"].values()))
            c_rule = st.selectbox("진로 구성", list(RULE_OPTIONS["career"].values()))

        submitted = st.form_submit_button("분반 생성", use_container_width=True, type="primary")

    st.markdown("---")
    _render_question_editor()

    if submitted:
        if not section_name.strip():
            st.error("분반 이름을 입력하세요.")
            return
        if not uploaded:
            st.error("학생 명단 파일을 업로드하세요.")
            return

        df, err = parse_excel(uploaded)
        if err:
            st.error(f"파일 오류: {err}")
            return

        team_sizes = None
        if custom_sizes_input.strip():
            try:
                team_sizes = [int(x.strip()) for x in custom_sizes_input.split(",")]
            except ValueError:
                st.error("팀별 인원 수는 숫자를 쉼표로 구분해 입력하세요. 예: 4,3,3")
                return
            if len(team_sizes) != int(num_teams):
                st.error(f"팀 수({int(num_teams)})와 입력한 인원 수 항목 개수({len(team_sizes)})가 다릅니다.")
                return
            if sum(team_sizes) != len(df):
                st.error(f"인원 수 합계({sum(team_sizes)})가 전체 학생 수({len(df)})와 다릅니다.")
                return

        def reverse_lookup(options_dict, label):
            for k, v in options_dict.items():
                if v == label:
                    return k
            return list(options_dict.keys())[0]

        rules = {
            "personality": reverse_lookup(RULE_OPTIONS["personality"], p_rule),
            "gender": reverse_lookup(RULE_OPTIONS["gender"], g_rule),
            "mbti": reverse_lookup(RULE_OPTIONS["mbti"], m_rule),
            "mbti_ei": reverse_lookup(RULE_OPTIONS["mbti_ei"], ei_rule),
            "department": reverse_lookup(RULE_OPTIONS["department"], d_rule),
            "career": reverse_lookup(RULE_OPTIONS["career"], c_rule),
        }

        custom_questions = {
            pt: list(qs)
            for pt, qs in st.session_state.get("section_questions", {}).items()
        }

        db = get_db()
        sec_ref = db.collection("sections").document()
        prof = st.session_state.get("professor", {})
        sec_ref.set({
            "name": section_name.strip(),
            "num_teams": int(num_teams),
            "team_sizes": team_sizes,
            "rules": rules,
            "custom_questions": custom_questions,
            "teams_published": False,
            "survey_closed": False,
            "professor_id": prof.get("id", ""),
            "created_at": datetime.now().isoformat(),
        })

        batch = db.batch()
        for _, row in df.iterrows():
            ref = db.collection("students").document()
            batch.set(ref, {
                "name": row["name"],
                "student_id": row["student_id"],
                "email": row["email"],
                "department": row.get("department", ""),
                "grade": str(row.get("grade", "")),
                "section_id": sec_ref.id,
                "survey_completed": False,
                "gender": "",
                "mbti": "",
                "career": "",
                "personality_type": "",
                "personality_scores": {},
                "created_at": datetime.now().isoformat(),
            })
        batch.commit()

        st.success(f"'{section_name}' 분반이 생성되었습니다. (학생 {len(df)}명 등록)")
        st.session_state.pop("section_questions", None)
        st.session_state.pop("q_tpl_ver", None)
        st.session_state["page"] = "admin_dashboard"
        st.rerun()


# ──────────────────────────────────────────
# 페이지: 분반 현황
# ──────────────────────────────────────────

def page_admin_section_detail():
    section_id = st.session_state.get("cur_section", "")
    section = get_section(section_id)
    if not section:
        st.error("분반을 찾을 수 없습니다.")
        return

    st.markdown(f"## {section['name']} — 현황")
    if st.button("← 대시보드"):
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    st.markdown("---")

    students = get_students_in_section(section_id)
    done = [s for s in students if s.get("survey_completed", False)]
    pending = [s for s in students if not s.get("survey_completed", False)]

    c1, c2, c3 = st.columns(3)
    c1.metric("전체", len(students))
    c2.metric("완료", len(done))
    c3.metric("미완료", len(pending))

    if len(done) == len(students) and students:
        st.success("✅ 모든 학생이 설문을 완료했습니다!")
    else:
        pct = int(len(done) / len(students) * 100) if students else 0
        st.progress(pct / 100, text=f"{pct}% 완료")

    # 참여 중지 / 재개 버튼
    is_closed = section.get("survey_closed", False)
    is_published = section.get("teams_published", False)
    if not is_published:
        st.markdown("---")
        if is_closed:
            st.error("🔒 설문이 마감되었습니다. 미완료 학생은 더 이상 제출할 수 없습니다.")
            col_reopen, col_go = st.columns(2)
            if col_reopen.button("🔓 참여 재개", use_container_width=True):
                get_db().collection("sections").document(section_id).update({"survey_closed": False})
                st.rerun()
            if col_go.button("팀 편성하러 가기 →", use_container_width=True, type="primary"):
                st.session_state.update({"page": "admin_team_formation", "cur_section": section_id})
                st.rerun()
        else:
            if pending:
                if st.button("🔒 참여 중지 (팀 편성 시작)", use_container_width=True, type="primary"):
                    get_db().collection("sections").document(section_id).update({"survey_closed": True})
                    st.rerun()
            else:
                st.success("모든 학생이 완료했습니다. 팀 편성을 진행하세요.")

    st.markdown("---")
    tab1, tab2 = st.tabs(["✅ 완료", "⏳ 미완료"])

    with tab1:
        if done:
            st.dataframe(pd.DataFrame([{
                "이름": s["name"],
                "학과": s.get("department", ""),
                "성별": s.get("gender", ""),
                "성향": s.get("personality_type", ""),
                "MBTI": s.get("mbti", ""),
                "완료시간": s.get("survey_completed_at", "")[:16],
            } for s in done]), use_container_width=True, hide_index=True)
        else:
            st.info("아직 완료한 학생이 없습니다.")

    with tab2:
        if pending:
            st.dataframe(pd.DataFrame([{
                "이름": s["name"],
                "학과": s.get("department", ""),
                "이메일": s.get("email", ""),
            } for s in pending]), use_container_width=True, hide_index=True)
        else:
            st.info("미완료 학생이 없습니다.")


# ──────────────────────────────────────────
# 페이지: 팀 편성
# ──────────────────────────────────────────

def page_admin_team_formation():
    section_id = st.session_state.get("cur_section", "")
    section = get_section(section_id)
    if not section:
        st.error("분반을 찾을 수 없습니다.")
        return

    st.markdown(f"## {section['name']} — 팀 편성")
    col_back1, col_back2 = st.columns([1, 1])
    if col_back1.button("← 대시보드"):
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    if col_back2.button("← 현황보기"):
        st.session_state["page"] = "admin_section_detail"
        st.rerun()
    st.markdown("---")

    students = get_students_in_section(section_id)
    done = [s for s in students if s.get("survey_completed", False)]

    c1, c2, c3 = st.columns(3)
    c1.metric("전체 학생", len(students))
    c2.metric("설문 완료", len(done))
    c3.metric("미완료", len(students) - len(done))

    if len(done) < len(students):
        st.warning(f"⚠️ {len(students) - len(done)}명이 아직 설문을 완료하지 않았습니다. 그래도 편성할 수 있습니다.")

    st.markdown("---")

    existing = get_teams(section_id)
    is_published = existing and existing.get("published", False)

    if not is_published:
        if st.button("🔀 팀 편성 실행", type="primary", use_container_width=True):
            with st.spinner("팀 편성 중..."):
                teams = form_teams(done, section["num_teams"], section.get("rules", {}), section.get("team_sizes"))
                serialized = serialize_teams(teams)
                db = get_db()
                teams_doc = encode_teams(serialized)
                teams_doc.update({"published": False, "created_at": datetime.now().isoformat()})
                db.collection("teams").document(section_id).set(teams_doc)
                st.session_state["draft_teams"] = serialized
            st.success("팀 편성 완료! 아래에서 확인하고 수정하세요.")
            st.rerun()

    # 편집/표시할 팀 데이터 결정
    if is_published:
        teams_data = decode_teams(existing)
        _show_published_teams(teams_data, section_id)
    elif existing or "draft_teams" in st.session_state:
        teams_data = st.session_state.get("draft_teams") or decode_teams(existing)
        _show_draft_teams(teams_data, section_id, section)


def _show_draft_teams(teams_data, section_id, section):
    # 저장 후 미리보기 모드
    if st.session_state.get("draft_preview"):
        st.info("저장된 팀 구성입니다. 추가 수정하거나 공개하세요.")
        for i, team in enumerate(teams_data):
            with st.expander(f"{i + 1}팀 ({len(team)}명)", expanded=True):
                st.dataframe(pd.DataFrame([{
                    "이름": m["name"],
                    "학과": m.get("department", ""),
                    "성향": m.get("personality_type", ""),
                    "MBTI": m.get("mbti", ""),
                    "성별": m.get("gender", ""),
                } for m in team]), use_container_width=True, hide_index=True)

        st.markdown("---")
        col_edit, col_email_toggle, col_publish = st.columns([1, 1, 1])
        with col_edit:
            if col_edit.button("✏️ 다시 편집", use_container_width=True):
                st.session_state["draft_preview"] = False
                st.rerun()
        with col_email_toggle:
            send_email = st.checkbox("이메일 발송", value=True, key="email_toggle_preview")
        with col_publish:
            if col_publish.button("📢 공개하기", use_container_width=True, type="primary"):
                db = get_db()
                teams_doc = encode_teams(teams_data)
                teams_doc.update({"published": True, "published_at": datetime.now().isoformat()})
                db.collection("teams").document(section_id).set(teams_doc)
                db.collection("sections").document(section_id).update({"teams_published": True})
                for key in ["draft_teams", "draft_preview"]:
                    st.session_state.pop(key, None)
                if send_email:
                    st.session_state.update({
                        "page": "admin_send_email",
                        "email_teams": teams_data,
                        "email_section_name": section["name"],
                    })
                else:
                    st.session_state["page"] = "admin_dashboard"
                st.rerun()
        return

    # 편집 모드
    st.subheader("팀 구성 (수정 가능)")
    st.caption("우측 숫자로 학생의 팀을 변경한 뒤 저장하세요.")

    edited = copy.deepcopy(teams_data)

    for i, team in enumerate(edited):
        with st.expander(f"{i + 1}팀 ({len(team)}명)", expanded=True):
            for j, m in enumerate(team):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**{m['name']}**")
                c2.write(m.get("department", ""))
                c3.write(f"{m.get('personality_type', '')} / {m.get('mbti', '')}")
                new_t = c4.selectbox(
                    "팀",
                    options=list(range(1, len(edited) + 1)),
                    index=i,
                    key=f"assign_{i}_{j}",
                    label_visibility="collapsed",
                )
                m["_new_team"] = new_t

    st.markdown("---")
    col_save, col_email_toggle, col_publish = st.columns([1, 1, 1])

    with col_save:
        if st.button("💾 저장 후 확인", use_container_width=True, type="primary"):
            new_teams = _apply_moves(edited)
            db = get_db()
            teams_doc = encode_teams(new_teams)
            teams_doc.update({"published": False, "updated_at": datetime.now().isoformat()})
            db.collection("teams").document(section_id).set(teams_doc)
            st.session_state["draft_teams"] = new_teams
            st.session_state["draft_preview"] = True
            st.rerun()

    with col_email_toggle:
        send_email = st.checkbox("이메일 발송", value=True)

    with col_publish:
        if st.button("📢 공개하기", use_container_width=True):
            new_teams = _apply_moves(edited)
            db = get_db()
            teams_doc = encode_teams(new_teams)
            teams_doc.update({"published": True, "published_at": datetime.now().isoformat()})
            db.collection("teams").document(section_id).set(teams_doc)
            db.collection("sections").document(section_id).update({"teams_published": True})
            for key in ["draft_teams", "draft_preview"]:
                st.session_state.pop(key, None)
            if send_email:
                st.session_state.update({
                    "page": "admin_send_email",
                    "email_teams": new_teams,
                    "email_section_name": section["name"],
                })
            else:
                st.session_state["page"] = "admin_dashboard"
            st.rerun()


def _show_published_teams(teams_data, section_id):
    col_status, col_cancel = st.columns([3, 1])
    col_status.success("✅ 팀이 공개되었습니다.")
    if col_cancel.button("공개 취소", use_container_width=True):
        db = get_db()
        db.collection("teams").document(section_id).update({"published": False})
        db.collection("sections").document(section_id).update({"teams_published": False})
        st.session_state.pop("draft_preview", None)
        st.rerun()

    for i, team in enumerate(teams_data):
        with st.expander(f"{i + 1}팀 ({len(team)}명)"):
            st.dataframe(pd.DataFrame([{
                "이름": m["name"],
                "학과": m.get("department", ""),
                "성향": m.get("personality_type", ""),
                "MBTI": m.get("mbti", ""),
                "성별": m.get("gender", ""),
            } for m in team]), use_container_width=True, hide_index=True)


def _apply_moves(edited_teams):
    n = len(edited_teams)
    new_teams = [[] for _ in range(n)]
    for i, team in enumerate(edited_teams):
        for m in team:
            target = m.pop("_new_team", i + 1)
            target = max(1, min(target, n)) - 1
            clean = {k: v for k, v in m.items() if not k.startswith("_")}
            new_teams[target].append(clean)
    return new_teams


# ──────────────────────────────────────────
# 페이지: 이메일 발송
# ──────────────────────────────────────────

def page_admin_send_email():
    st.markdown("## 이메일 발송")
    st.markdown("---")

    teams = st.session_state.get("email_teams", [])
    section_name = st.session_state.get("email_section_name", "")

    st.write(f"**{section_name}** 수업 팀원 명단을 학생 이메일로 발송합니다.")
    st.info("Gmail 앱 비밀번호가 필요합니다. (Google 계정 → 보안 → 앱 비밀번호)")

    sender_email = st.text_input("발신자 Gmail 주소", value=st.secrets.get("email", {}).get("sender", ""))
    sender_password = st.text_input("앱 비밀번호 (16자리)", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📧 이메일 발송", type="primary", use_container_width=True):
            if not sender_email or not sender_password:
                st.error("이메일 주소와 앱 비밀번호를 입력하세요.")
                return
            with st.spinner("발송 중..."):
                results = send_team_emails(teams, section_name, sender_email, sender_password)
            for r in results:
                st.write(r)
    with col2:
        if st.button("건너뛰기", use_container_width=True):
            st.session_state["page"] = "admin_dashboard"
            st.rerun()


# ──────────────────────────────────────────
# 메인 라우터
# ──────────────────────────────────────────

# ──────────────────────────────────────────
# 페이지: 분반 설정 수정
# ──────────────────────────────────────────

def page_admin_edit_section():
    section_id = st.session_state.get("cur_section", "")
    section = get_section(section_id)
    if not section:
        st.error("분반을 찾을 수 없습니다.")
        return

    st.markdown(f"## 설정 수정 — {section['name']}")
    if st.button("← 대시보드"):
        st.session_state["page"] = "admin_dashboard"
        st.rerun()
    st.markdown("---")
    st.caption("학생 명단은 변경되지 않습니다. 이름, 팀 수, 구성 규칙만 수정됩니다.")

    cur_rules = section.get("rules", {})
    cur_extra = section.get("extra_questions", {})

    def rule_index(rule_dict, current_val):
        keys = list(rule_dict.keys())
        return keys.index(current_val) if current_val in keys else 0

    cur_sizes = section.get("team_sizes")
    cur_sizes_str = ",".join(str(x) for x in cur_sizes) if cur_sizes else ""

    with st.form("edit_section_form"):
        section_name = st.text_input("분반 이름", value=section.get("name", ""))
        num_teams = st.number_input("팀 수", min_value=2, max_value=20, value=section.get("num_teams", 5))
        custom_sizes_input = st.text_input(
            "팀별 인원 수 (선택)",
            value=cur_sizes_str,
            placeholder="예: 2,3,5 — 비워두면 자동 균등 배분",
            help="팀 수만큼 쉼표로 구분해 입력하세요. 합계는 설문 완료 학생 수와 일치해야 합니다.",
        )

        st.markdown("#### 팀 구성 규칙")
        col1, col2 = st.columns(2)
        with col1:
            p_labels = list(RULE_OPTIONS["personality"].values())
            p_rule = st.selectbox("성향 구성", p_labels,
                index=rule_index(RULE_OPTIONS["personality"], cur_rules.get("personality", "mixed")))
            g_labels = list(RULE_OPTIONS["gender"].values())
            g_rule = st.selectbox("성별 구성", g_labels,
                index=rule_index(RULE_OPTIONS["gender"], cur_rules.get("gender", "balanced")))
            m_labels = list(RULE_OPTIONS["mbti"].values())
            m_rule = st.selectbox("MBTI 구성", m_labels,
                index=rule_index(RULE_OPTIONS["mbti"], cur_rules.get("mbti", "mixed")))
        with col2:
            ei_labels = list(RULE_OPTIONS["mbti_ei"].values())
            ei_rule = st.selectbox("E/I 성향", ei_labels,
                index=rule_index(RULE_OPTIONS["mbti_ei"], cur_rules.get("mbti_ei", "balanced")))
            d_labels = list(RULE_OPTIONS["department"].values())
            d_rule = st.selectbox("학과 구성", d_labels,
                index=rule_index(RULE_OPTIONS["department"], cur_rules.get("department", "mixed")))
            c_labels = list(RULE_OPTIONS["career"].values())
            c_rule = st.selectbox("진로 구성", c_labels,
                index=rule_index(RULE_OPTIONS["career"], cur_rules.get("career", "none")))

        st.markdown("#### 추가 질문 수정")
        st.caption("한 줄에 하나씩 입력하세요. 기존 질문은 유지되며 여기서 추가/삭제만 됩니다.")
        extra_inputs = {}
        for pt in PERSONALITY_TYPES:
            existing = "\n".join(cur_extra.get(pt, []))
            extra_inputs[pt] = st.text_area(f"{pt} 추가 질문", value=existing, height=80)

        submitted = st.form_submit_button("저장", use_container_width=True, type="primary")

    if submitted:
        new_team_sizes = None
        if custom_sizes_input.strip():
            try:
                new_team_sizes = [int(x.strip()) for x in custom_sizes_input.split(",")]
            except ValueError:
                st.error("팀별 인원 수는 숫자를 쉼표로 구분해 입력하세요. 예: 2,3,5")
                st.stop()
            if len(new_team_sizes) != int(num_teams):
                st.error(f"팀 수({int(num_teams)})와 입력한 항목 개수({len(new_team_sizes)})가 다릅니다.")
                st.stop()

        def reverse_lookup(options_dict, label):
            for k, v in options_dict.items():
                if v == label:
                    return k
            return list(options_dict.keys())[0]

        new_rules = {
            "personality": reverse_lookup(RULE_OPTIONS["personality"], p_rule),
            "gender": reverse_lookup(RULE_OPTIONS["gender"], g_rule),
            "mbti": reverse_lookup(RULE_OPTIONS["mbti"], m_rule),
            "mbti_ei": reverse_lookup(RULE_OPTIONS["mbti_ei"], ei_rule),
            "department": reverse_lookup(RULE_OPTIONS["department"], d_rule),
            "career": reverse_lookup(RULE_OPTIONS["career"], c_rule),
        }

        new_extra = {}
        for pt, text in extra_inputs.items():
            lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
            if lines:
                new_extra[pt] = lines

        db = get_db()
        db.collection("sections").document(section_id).update({
            "name": section_name.strip(),
            "num_teams": int(num_teams),
            "team_sizes": new_team_sizes,
            "rules": new_rules,
            "extra_questions": new_extra,
            "updated_at": datetime.now().isoformat(),
        })

        st.success("설정이 저장되었습니다!")
        st.session_state["page"] = "admin_dashboard"
        st.rerun()


def _inject_css():
    st.markdown("""
<style>
/* ══════════════════════════════════════
   PAGE SHELL
══════════════════════════════════════ */
[data-testid="stAppViewContainer"] {
    background: #E8EDF5 !important;
}
[data-testid="stHeader"] {
    background: transparent !important;
}
/* Streamlit 상단 툴바 숨김 */
[data-testid="stToolbar"] { display: none !important; }

/* 메인 컨텐츠를 흰 카드로 */
.main .block-container {
    background: #FFFFFF;
    border-radius: 20px;
    padding: 2rem 2.5rem 3rem;
    max-width: 900px;
    margin: 1.5rem auto 2rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04);
}

/* ══════════════════════════════════════
   TYPOGRAPHY
══════════════════════════════════════ */
h2 {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    margin-bottom: 0.15rem !important;
    letter-spacing: -0.02em !important;
}
h3 {
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    letter-spacing: -0.01em !important;
}
h4 {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    color: #334155 !important;
}

/* ══════════════════════════════════════
   BUTTONS — 기본
══════════════════════════════════════ */
[data-testid="stButton"] > button {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.8rem !important;
    white-space: nowrap !important;
    min-height: 34px !important;
    border: 1.5px solid #DDE3EE !important;
    background: #FFFFFF !important;
    color: #475569 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    transition: all 0.15s ease !important;
    line-height: 1.4 !important;
}
[data-testid="stButton"] > button:hover {
    border-color: #6366F1 !important;
    color: #4F46E5 !important;
    background: #F5F3FF !important;
    box-shadow: 0 2px 6px rgba(99,102,241,0.15) !important;
}

/* BUTTONS — 프라이머리 */
[data-testid="stButton"] > button[kind="primary"] {
    background: #4F46E5 !important;
    color: #FFFFFF !important;
    border-color: transparent !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.3) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #4338CA !important;
    box-shadow: 0 4px 14px rgba(79,70,229,0.4) !important;
    transform: translateY(-1px) !important;
    border-color: transparent !important;
    color: #FFFFFF !important;
}

/* ══════════════════════════════════════
   INPUT FIELDS
══════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div {
    border-radius: 8px !important;
    border: 1.5px solid #DDE3EE !important;
    font-size: 14px !important;
    background: #FAFBFF !important;
    color: #1E293B !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #6366F1 !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
}
/* 폼 테두리 제거 */
[data-testid="stForm"] { border: none !important; padding: 0 !important; }

/* ══════════════════════════════════════
   METRIC CARDS
══════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #F8FAFF !important;
    border: 1px solid #E0E7FF !important;
    border-left: 3px solid #6366F1 !important;
    border-radius: 10px !important;
    padding: 0.9rem 1.1rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
[data-testid="stMetricValue"] {
    color: #4F46E5 !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] { color: #64748B !important; font-size: 12px !important; }

/* ══════════════════════════════════════
   EXPANDER (분반 카드)
══════════════════════════════════════ */
[data-testid="stExpander"] {
    border: 1px solid #E8ECF4 !important;
    border-radius: 14px !important;
    margin-bottom: 0.8rem !important;
    background: #FFFFFF !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    overflow: hidden !important;
    transition: box-shadow 0.2s ease !important;
}
[data-testid="stExpander"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.09) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 0.9rem 1.1rem !important;
    color: #1E293B !important;
    background: #FAFBFF !important;
}

/* ══════════════════════════════════════
   PROGRESS BAR
══════════════════════════════════════ */
[data-testid="stProgressBar"] > div > div > div {
    background: linear-gradient(90deg, #6366F1, #8B5CF6) !important;
    border-radius: 99px !important;
}

/* ══════════════════════════════════════
   MISC
══════════════════════════════════════ */
/* 구분선 */
hr {
    margin: 1.25rem 0 !important;
    border: none !important;
    border-top: 1px solid #F1F5F9 !important;
}
/* 라디오 */
[data-testid="stRadio"] label { font-size: 14px !important; }
/* 알림 박스 */
[data-testid="stAlert"] { border-radius: 10px !important; font-size: 13px !important; }
/* 탭 */
[data-testid="stTabs"] [role="tab"] { font-size: 14px !important; font-weight: 500 !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #6366F1 !important;
    border-bottom-color: #6366F1 !important;
}
/* 데이터프레임 */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #E8ECF4 !important;
}
/* 캡션 */
[data-testid="stCaptionContainer"] p { color: #94A3B8 !important; font-size: 12px !important; }
/* 컨테이너 border */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 14px !important;
    border-color: #E8ECF4 !important;
}
</style>
""", unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="팀 편성 시스템", page_icon="👥", layout="centered")
    _inject_css()

    page = st.session_state.get("page", "login")

    routes = {
        "login": page_login,
        "super_admin_setup": page_super_admin_setup,
        "professor_register": page_professor_register,
        "professor_change_password": page_professor_change_password,
        "super_admin_invite_codes": page_super_admin_invite_codes,
        "student_select_section": page_student_select_section,
        "student_main": page_student_main,
        "student_personality_result": page_student_personality_result,
        "admin_dashboard": page_admin_dashboard,
        "admin_professor_list": page_admin_professor_list,
        "admin_create_section": page_admin_create_section,
        "admin_edit_section": page_admin_edit_section,
        "admin_section_detail": page_admin_section_detail,
        "admin_team_formation": page_admin_team_formation,
        "admin_send_email": page_admin_send_email,
    }

    routes.get(page, page_login)()


if __name__ == "__main__":
    main()
