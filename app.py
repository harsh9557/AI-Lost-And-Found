"""AI Lost & Found - Streamlit application."""
import os
import uuid
from pathlib import Path

import streamlit as st
from PIL import Image

from database import (
    DB_NAME, create_database, create_user, login_user, add_item, get_item, get_items,
    add_notification, get_notifications, get_unread_count, mark_all_read,
    create_claim_request, get_received_claims, get_sent_claims, update_claim_status,
    get_claim_receiver, update_item_status, delete_item, send_chat_message,
    get_chat_messages, get_accepted_chats, get_dashboard_stats, get_all_users, make_admin,
)
from ai_matching import calculate_match, text_match, image_match

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="AI Lost & Found", page_icon="🔎", layout="wide")
create_database()

for key, default in {
    "logged_in": False, "user_id": None, "user_name": "", "username": "", "is_admin": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def save_photo(uploaded_file, prefix):
    if not uploaded_file:
        return ""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        raise ValueError("Please upload a JPG, PNG, WEBP, or BMP image.")
    # Decode once to reject invalid or corrupt image uploads.
    try:
        image = Image.open(uploaded_file)
        image.verify()
    except Exception as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc
    uploaded_file.seek(0)
    filename = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(uploaded_file.getbuffer())
    return str(destination)


def safe_delete_photo(path):
    if not path:
        return
    try:
        p = Path(path).resolve()
        if UPLOAD_DIR.resolve() in p.parents and p.is_file():
            p.unlink()
    except OSError:
        pass


def render_item_card(item, show_owner=False):
    cols = st.columns([1, 2])
    with cols[0]:
        photo = item.get("photo", "")
        if photo and Path(photo).is_file():
            st.image(photo, use_container_width=True)
        else:
            st.caption("No photo uploaded")
    with cols[1]:
        st.subheader(f"{item.get('item_name', 'Unnamed item')}  ·  #{item.get('id')}")
        st.write(f"**Type:** {item.get('item_type', '')}  |  **Status:** {item.get('status', 'Active')}")
        st.write(f"**Color:** {item.get('color') or 'Not specified'}")
        st.write(f"**Location:** {item.get('location') or 'Not specified'}")
        st.write(item.get("description") or "No description provided.")
        st.caption(f"Reported: {item.get('uploaded_at') or 'Date unavailable'}")
        if show_owner and item.get("reporter_name"):
            st.caption(f"Reported by: {item['reporter_name']}")


def make_notifications():
    """Only process active cross-user pairs; DB uniqueness prevents duplicate alerts."""
    lost_items = get_items("Lost", "Active", limit=300)
    found_items = get_items("Found", "Active", limit=300)
    count = 0
    for lost in lost_items:
        for found in found_items:
            if not lost.get("user_id") or not found.get("user_id") or lost["user_id"] == found["user_id"]:
                continue
            score = calculate_match(lost, found)
            if score < 50:
                continue
            msg = f"Possible match ({score:.0f}%): '{lost['item_name']}' may match '{found['item_name']}'."
            add_notification(lost["user_id"], lost["id"], found["id"], msg, score)
            add_notification(found["user_id"], lost["id"], found["id"], msg, score)
            count += 1
    return count


def logout():
    for key, value in {"logged_in": False, "user_id": None, "user_name": "", "username": "", "is_admin": False}.items():
        st.session_state[key] = value
    st.rerun()


# Authentication screen
if not st.session_state.logged_in:
    st.title("🔎 AI Lost & Found")
    st.write("Report missing belongings, discover possible matches, and contact the reporter safely.")
    login_tab, signup_tab = st.tabs(["🔐 Login", "📝 Create account"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            user = login_user(username, password) if username.strip() and password else None
            if user:
                st.session_state.update(logged_in=True, user_id=user[0], user_name=user[1], username=user[2], is_admin=bool(user[3]))
                st.rerun()
            st.error("Invalid username or password.")
    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            new_username = st.text_input("Choose username")
            new_password = st.text_input("Password (minimum 8 characters)", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if new_password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = create_user(name, new_username, new_password)
                (st.success if ok else st.error)(message)
    st.stop()

# Sidebar navigation
st.sidebar.title("🔎 AI Lost & Found")
st.sidebar.success(f"👤 {st.session_state.user_name}")
st.sidebar.caption(f"@{st.session_state.username}")
if st.session_state.is_admin:
    st.sidebar.info("👑 Administrator")
unread = get_unread_count(st.session_state.user_id)
menus = ["🏠 Home", "📌 Report Lost", "📦 Report Found", "🤖 AI Matching", "📂 My Reports", f"🔔 Notifications ({unread})" if unread else "🔔 Notifications", "🤝 Claim Requests", "💬 Chat", "📊 Dashboard"]
if st.session_state.is_admin:
    menus.append("👨‍💼 Admin Panel")
menu = st.sidebar.radio("Navigation", menus)
if st.sidebar.button("🚪 Logout", use_container_width=True):
    logout()
st.sidebar.caption("Use accurate descriptions and only upload photos you are allowed to share.")

# Home
if menu == "🏠 Home":
    st.title("🔎 AI Lost & Found")
    st.subheader(f"Welcome, {st.session_state.user_name}!")
    stats = get_dashboard_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lost reports", stats["lost"]); c2.metric("Found reports", stats["found"])
    c3.metric("Active items", stats["active"]); c4.metric("Registered users", stats["users"])
    st.divider()
    st.markdown("### How it works")
    a, b, c = st.columns(3)
    a.info("**1. Report**\n\nSubmit details about an item you lost or found.")
    b.info("**2. AI matching**\n\nThe system compares descriptions and, when available, photos.")
    c.success("**3. Connect**\n\nSend a claim request and discuss an accepted claim in chat.")
    st.caption("AI scores are suggestions, not proof of ownership. Verify details privately before handing over an item.")
    st.subheader("Latest active reports")
    latest = get_items(status="Active", limit=6)
    if not latest:
        st.info("No reports yet. Use Report Lost or Report Found to add one.")
    for item in latest:
        with st.container(border=True):
            render_item_card(item, show_owner=True)

# Report forms
elif menu in ("📌 Report Lost", "📦 Report Found"):
    item_type = "Lost" if menu == "📌 Report Lost" else "Found"
    st.title(f"{ '📌 Report a Lost Item' if item_type == 'Lost' else '📦 Report a Found Item' }")
    with st.form(f"report_{item_type.lower()}_form", clear_on_submit=True):
        name = st.text_input("Item name *", max_chars=100)
        description = st.text_area("Description *", max_chars=1000, placeholder="Brand, identifying marks, contents (avoid sharing sensitive details publicly)…")
        color = st.text_input("Color", max_chars=50)
        location = st.text_input("Location where lost/found *", max_chars=150)
        photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png", "webp", "bmp"])
        submitted = st.form_submit_button("Submit report", use_container_width=True)
    if submitted:
        if not name.strip() or not description.strip() or not location.strip():
            st.error("Please complete Item name, Description, and Location.")
        else:
            try:
                photo_path = save_photo(photo, item_type.lower()) if photo else ""
                add_item(item_type, name, description, color, location, photo_path, st.session_state.user_id)
                st.success("Report submitted successfully!")
                st.info("Open AI Matching to check possible matches and generate notifications.")
            except (ValueError, OSError) as exc:
                st.error(str(exc))

# AI matching
elif menu == "🤖 AI Matching":
    st.title("🤖 AI Matching")
    st.write("Compare active lost and found reports. Results are ranked suggestions only.")
    if st.button("🔄 Find matches and create notifications", type="primary"):
        with st.spinner("Comparing reports…"):
            matches_created = make_notifications()
        st.success(f"Matching scan complete. {matches_created} possible pair(s) met the threshold. Duplicate notifications are skipped automatically.")
    lost_items = get_items("Lost", "Active", limit=300)
    found_items = get_items("Found", "Active", limit=300)
    results = []
    for lost in lost_items:
        for found in found_items:
            if lost.get("user_id") == found.get("user_id"):
                continue
            score = calculate_match(lost, found)
            if score >= 35:
                results.append((score, lost, found))
    results.sort(key=lambda x: x[0], reverse=True)
    if not results:
        st.info("No likely matches yet. Add reports with clear descriptions/photos and run matching again.")
    for score, lost, found in results[:30]:
        with st.container(border=True):
            st.subheader(f"Possible match · {score:.1f}%")
            left, right = st.columns(2)
            with left:
                st.markdown("**🔴 Lost report**")
                render_item_card(lost, show_owner=True)
            with right:
                st.markdown("**🟢 Found report**")
                render_item_card(found, show_owner=True)
                if found.get("user_id") != st.session_state.user_id and lost.get("user_id") == st.session_state.user_id:
                    with st.form(f"claim_{found['id']}_{lost['id']}"):
                        claim_message = st.text_area("Claim message", value=f"I reported a lost {lost['item_name']}. I may be able to verify ownership.", max_chars=1000, key=f"claim_msg_{found['id']}_{lost['id']}")
                        send = st.form_submit_button("Send claim request")
                    if send:
                        ok, msg = create_claim_request(found["id"], st.session_state.user_id, found["user_id"], claim_message)
                        (st.success if ok else st.warning)(msg)

# My reports
elif menu == "📂 My Reports":
    st.title("📂 My Reports")
    reports = get_items(user_id=st.session_state.user_id, limit=500)
    if not reports:
        st.info("You have not submitted any reports yet.")
    for item in reports:
        with st.container(border=True):
            render_item_card(item)
            col1, col2 = st.columns(2)
            if item["status"] == "Active":
                if col1.button("Mark closed", key=f"close_{item['id']}"):
                    update_item_status(item["id"], "Closed", st.session_state.user_id); st.rerun()
            if col2.button("Delete report", key=f"delete_{item['id']}"):
                path = delete_item(item["id"], st.session_state.user_id)
                safe_delete_photo(path)
                st.success("Report deleted."); st.rerun()

# Notifications
elif menu.startswith("🔔 Notifications"):
    st.title("🔔 Notifications")
    notifications = get_notifications(st.session_state.user_id)
    if st.button("Mark all as read"):
        mark_all_read(st.session_state.user_id); st.rerun()
    if not notifications:
        st.info("No notifications yet. Run AI Matching after reports are available.")
    for n in notifications:
        with st.container(border=True):
            st.write(("🟠 " if not n["is_read"] else "⚪ ") + n["message"])
            st.caption(f"Match score: {n['match_score']:.1f}% · {n['created_at']}")

# Claim requests
elif menu == "🤝 Claim Requests":
    st.title("🤝 Claim Requests")
    tab1, tab2 = st.tabs(["Received", "Sent"])
    with tab1:
        requests = get_received_claims(st.session_state.user_id)
        if not requests: st.info("No claim requests received.")
        for r in requests:
            with st.container(border=True):
                st.subheader(f"{r[6]} · Request #{r[0]}")
                st.write(f"From: **{r[8]}** · Status: **{r[4]}**")
                st.write(r[3]); st.caption(r[5])
                if r[4] == "Pending":
                    x, y = st.columns(2)
                    if x.button("Accept", key=f"accept_{r[0]}"):
                        update_claim_status(r[0], "Accepted", st.session_state.user_id); st.success("Request accepted. Chat is now available."); st.rerun()
                    if y.button("Reject", key=f"reject_{r[0]}"):
                        update_claim_status(r[0], "Rejected", st.session_state.user_id); st.rerun()
    with tab2:
        requests = get_sent_claims(st.session_state.user_id)
        if not requests: st.info("You have not sent any claim requests.")
        for r in requests:
            with st.container(border=True):
                st.subheader(f"{r[5]} · Request #{r[0]}")
                st.write(f"To: **{r[6]}** · Status: **{r[3]}**")
                st.write(r[2]); st.caption(r[4])

# Chat
elif menu == "💬 Chat":
    st.title("💬 Chat")
    chats = get_accepted_chats(st.session_state.user_id)
    if not chats:
        st.info("Chats become available after a claim request is accepted.")
    else:
        labels = {f"Request #{c[0]} · {c[6]} · {c[7] if c[2] != st.session_state.user_id else c[8]}": c for c in chats}
        selected_label = st.selectbox("Choose conversation", list(labels))
        claim = labels[selected_label]
        claim_id, item_id, sender_id, receiver_id = claim[:4]
        other_id = receiver_id if st.session_state.user_id == sender_id else sender_id
        messages = get_chat_messages(claim_id, st.session_state.user_id)
        for m in messages:
            who = "You" if m[1] == st.session_state.user_id else m[2]
            st.markdown(f"**{who}** · {m[4]}\n\n{m[3]}")
            st.divider()
        with st.form("chat_send_form", clear_on_submit=True):
            message = st.text_input("Message", max_chars=2000)
            sent = st.form_submit_button("Send")
        if sent:
            if send_chat_message(claim_id, st.session_state.user_id, other_id, message): st.rerun()
            else: st.error("Message could not be sent. Make sure it is not empty.")

# Dashboard
elif menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    stats = get_dashboard_stats()
    cols = st.columns(5)
    for col, label, key in zip(cols, ["Lost", "Found", "Active", "Claimed", "Users"], ["lost", "found", "active", "claimed", "users"]):
        col.metric(label, stats[key])
    st.subheader("Recent active items")
    for item in get_items(status="Active", limit=10):
        with st.container(border=True): render_item_card(item, show_owner=True)

# Admin panel
elif menu == "👨‍💼 Admin Panel" and st.session_state.is_admin:
    st.title("👨‍💼 Admin Panel")
    st.warning("Admin actions can affect all users' records. Use carefully.")
    st.subheader("Users")
    users = get_all_users()
    if users:
        st.dataframe([{k: u[k] for k in ("id", "name", "username", "is_admin", "created_at")} for u in users], use_container_width=True, hide_index=True)
    with st.form("make_admin_form"):
        admin_username = st.text_input("Promote username to admin")
        promote = st.form_submit_button("Make admin")
    if promote:
        if make_admin(admin_username): st.success("Admin role updated."); st.rerun()
        else: st.error("Username not found.")
    st.subheader("All reports")
    for item in get_items(limit=500):
        with st.container(border=True):
            render_item_card(item, show_owner=True)
            a, b = st.columns(2)
            if a.button("Close report", key=f"admin_close_{item['id']}"):
                update_item_status(item["id"], "Closed"); st.rerun()
            if b.button("Delete report", key=f"admin_delete_{item['id']}"):
                path = delete_item(item["id"]); safe_delete_photo(path); st.rerun()

st.sidebar.divider()
st.sidebar.caption(f"Database: {Path(DB_NAME).name}")
