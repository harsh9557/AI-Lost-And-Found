import os
import streamlit as st

from database import (
    create_database,
    create_user,
    login_user,
    add_item,
    add_notification,
    get_notifications,
    get_unread_count,
    mark_all_read,
    create_claim_request,
    get_received_claims,
    get_sent_claims,
    update_claim_status,
    get_claim_receiver,
    update_item_status,
    delete_item,
    send_chat_message,
    get_chat_messages,
    get_accepted_chats,
    get_connection
)

from ai_matching import (
    calculate_match,
    text_match,
    image_match
)


# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="AI Lost & Found",
    page_icon="🔎",
    layout="wide"
)

os.makedirs("uploads", exist_ok=True)

create_database()


# =========================================
# SESSION STATE
# =========================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "username" not in st.session_state:
    st.session_state.username = ""

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# =========================================
# LOGIN / SIGNUP
# =========================================

if not st.session_state.logged_in:

    st.title("🔎 AI Lost & Found")

    st.write(
        "Find your lost belongings using Artificial Intelligence."
    )

    st.divider()

    login_tab, signup_tab = st.tabs(
        ["🔐 Login", "📝 Sign Up"]
    )


    # =====================================
    # LOGIN
    # =====================================

    with login_tab:

        st.header("🔐 Login")

        username = st.text_input(
            "Username",
            key="login_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "🔓 Login",
            use_container_width=True
        ):

            if not username or not password:

                st.warning(
                    "⚠️ Please enter username and password."
                )

            else:

                user = login_user(
                    username,
                    password
                )

                if user:

                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = user[1]
                    st.session_state.username = user[2]
                    st.session_state.is_admin = bool(
                        user[3]
                    )

                    st.rerun()

                else:

                    st.error(
                        "❌ Invalid username or password."
                    )


    # =====================================
    # SIGNUP
    # =====================================

    with signup_tab:

        st.header("📝 Create Account")

        name = st.text_input(
            "Full Name",
            key="signup_name"
        )

        username = st.text_input(
            "Create Username",
            key="signup_username"
        )

        password = st.text_input(
            "Create Password",
            type="password",
            key="signup_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="signup_confirm"
        )

        if st.button(
            "📝 Create Account",
            use_container_width=True
        ):

            if not name or not username or not password:

                st.warning(
                    "⚠️ Please fill all fields."
                )

            elif password != confirm_password:

                st.error(
                    "❌ Passwords do not match."
                )

            else:

                success, message = create_user(
                    name,
                    username,
                    password
                )

                if success:

                    st.success(
                        "✅ Account created successfully!"
                    )

                    st.info(
                        "Now login with your account."
                    )

                else:

                    st.error(
                        "❌ " + message
                    )

    st.stop()


# =========================================
# GENERATE AI NOTIFICATIONS
# =========================================

def generate_notifications():

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            id,
            item_name,
            description,
            color,
            location,
            photo,
            user_id
        FROM items
        WHERE item_type = 'Lost'
        AND status = 'Active'
        AND user_id IS NOT NULL
    """)

    lost_items = cursor.fetchall()


    cursor.execute("""
        SELECT
            id,
            item_name,
            description,
            color,
            location,
            photo,
            user_id
        FROM items
        WHERE item_type = 'Found'
        AND status = 'Active'
        AND user_id IS NOT NULL
    """)

    found_items = cursor.fetchall()

    conn.close()


    for lost in lost_items:

        lost_data = {
            "id": lost[0],
            "item_name": lost[1],
            "description": lost[2],
            "color": lost[3],
            "location": lost[4],
            "photo": lost[5],
            "user_id": lost[6]
        }


        for found in found_items:

            found_data = {
                "id": found[0],
                "item_name": found[1],
                "description": found[2],
                "color": found[3],
                "location": found[4],
                "photo": found[5],
                "user_id": found[6]
            }


            score = calculate_match(
                lost_data,
                found_data
            )


            if score >= 50:

                message = (
                    "Possible match found: "
                    + str(lost_data["item_name"])
                    + " may match "
                    + str(found_data["item_name"])
                    + "."
                )


                add_notification(
                    lost_data["user_id"],
                    lost_data["id"],
                    found_data["id"],
                    message,
                    score
                )


                if (
                    found_data["user_id"]
                    != lost_data["user_id"]
                ):

                    add_notification(
                        found_data["user_id"],
                        lost_data["id"],
                        found_data["id"],
                        message,
                        score
                    )


generate_notifications()


# =========================================
# SIDEBAR
# =========================================

st.sidebar.title("🔎 AI Lost & Found")

st.sidebar.success(
    "👤 " + st.session_state.user_name
)

st.sidebar.caption(
    "@" + st.session_state.username
)


if st.session_state.is_admin:

    st.sidebar.info(
        "👑 Administrator"
    )


unread_count = get_unread_count(
    st.session_state.user_id
)


if unread_count > 0:

    notification_menu = (
        "🔔 Notifications (" +
        str(unread_count) +
        ")"
    )

else:

    notification_menu = "🔔 Notifications"


st.sidebar.divider()


menu_items = [
    "🏠 Home",
    "📌 Report Lost Item",
    "📦 Report Found Item",
    "🤖 AI Matching",
    "📂 My Reports",
    notification_menu,
    "🤝 Claim Requests",
    "💬 Chat",
    "📊 Dashboard"
]


if st.session_state.is_admin:

    menu_items.append(
        "👨‍💼 Admin Panel"
    )


menu = st.sidebar.radio(
    "Menu",
    menu_items
)


# =========================================
# LOGOUT
# =========================================

st.sidebar.divider()

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.username = ""
    st.session_state.is_admin = False

    st.rerun()


# =========================================
# HOME
# =========================================

if menu == "🏠 Home":

    st.title("🔎 AI Lost & Found")

    st.header(
        "Welcome, "
        + st.session_state.user_name
        + " 👋"
    )

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE item_type='Lost'
    """)

    lost_count = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE item_type='Found'
    """)

    found_count = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
    """)

    total_count = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM users
    """)

    user_count = cursor.fetchone()[0]


    conn.close()


    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🔴 Lost",
        lost_count
    )

    c2.metric(
        "🟢 Found",
        found_count
    )

    c3.metric(
        "📦 Reports",
        total_count
    )

    c4.metric(
        "👥 Users",
        user_count
    )


    st.divider()

    st.subheader(
        "🤖 How AI Works"
    )

    a, b, c = st.columns(3)

    a.info(
        "1️⃣ Report\n\n"
        "Report your lost or found item."
    )

    b.info(
        "2️⃣ AI Matching\n\n"
        "AI compares text and images."
    )

    c.success(
        "3️⃣ Notification\n\n"
        "Possible matches are notified."
    )


# =========================================
# REPORT LOST
# =========================================

elif menu == "📌 Report Lost Item":

    st.header("📌 Report Lost Item")

    with st.form("lost_form"):

        item_name = st.text_input(
            "Item Name"
        )

        color = st.text_input(
            "Color"
        )

        location = st.text_input(
            "Lost Location"
        )

        description = st.text_area(
            "Description"
        )

        photo = st.file_uploader(
            "Upload Photo",
            type=[
                "jpg",
                "jpeg",
                "png"
            ]
        )

        submit = st.form_submit_button(
            "🚨 Report Lost Item"
        )


        if submit:

            if not item_name or not location:

                st.error(
                    "Please enter item name and location."
                )

            else:

                photo_path = ""

                if photo:

                    photo_path = os.path.join(
                        "uploads",
                        "lost_" + photo.name
                    )

                    with open(
                        photo_path,
                        "wb"
                    ) as file:

                        file.write(
                            photo.getbuffer()
                        )


                add_item(
                    "Lost",
                    item_name,
                    description,
                    color,
                    location,
                    photo_path,
                    st.session_state.user_id
                )

                st.success(
                    "✅ Lost item reported successfully!"
                )

                st.info(
                    "🕒 Date and time saved automatically."
                )


# =========================================
# REPORT FOUND
# =========================================

elif menu == "📦 Report Found Item":

    st.header("📦 Report Found Item")

    with st.form("found_form"):

        item_name = st.text_input(
            "Item Name"
        )

        color = st.text_input(
            "Color"
        )

        location = st.text_input(
            "Found Location"
        )

        description = st.text_area(
            "Description"
        )

        photo = st.file_uploader(
            "Upload Photo",
            type=[
                "jpg",
                "jpeg",
                "png"
            ]
        )

        submit = st.form_submit_button(
            "📦 Report Found Item"
        )


        if submit:

            if not item_name or not location:

                st.error(
                    "Please enter item name and location."
                )

            else:

                photo_path = ""

                if photo:

                    photo_path = os.path.join(
                        "uploads",
                        "found_" + photo.name
                    )

                    with open(
                        photo_path,
                        "wb"
                    ) as file:

                        file.write(
                            photo.getbuffer()
                        )


                add_item(
                    "Found",
                    item_name,
                    description,
                    color,
                    location,
                    photo_path,
                    st.session_state.user_id
                )

                st.success(
                    "✅ Found item reported successfully!"
                )

                st.info(
                    "🕒 Date and time saved automatically."
                )


# =========================================
# AI MATCHING
# =========================================

elif menu == "🤖 AI Matching":

    st.header("🤖 AI Matching")

    st.info(
        "🎯 Match score 50% or higher = Possible Match"
    )


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            id,
            item_name,
            description,
            color,
            location,
            photo,
            uploaded_at,
            user_id
        FROM items
        WHERE item_type='Lost'
        AND status='Active'
        ORDER BY id DESC
    """)

    lost_items = cursor.fetchall()


    cursor.execute("""
        SELECT
            id,
            item_name,
            description,
            color,
            location,
            photo,
            uploaded_at,
            user_id
        FROM items
        WHERE item_type='Found'
        AND status='Active'
        ORDER BY id DESC
    """)

    found_items = cursor.fetchall()

    conn.close()


    matches = 0


    for lost in lost_items:

        lost_data = {
            "id": lost[0],
            "item_name": lost[1],
            "description": lost[2],
            "color": lost[3],
            "location": lost[4],
            "photo": lost[5],
            "uploaded_at": lost[6],
            "user_id": lost[7]
        }


        for found in found_items:

            found_data = {
                "id": found[0],
                "item_name": found[1],
                "description": found[2],
                "color": found[3],
                "location": found[4],
                "photo": found[5],
                "uploaded_at": found[6],
                "user_id": found[7]
            }


            # Don't match user's own reports
            if (
                lost_data["user_id"]
                == found_data["user_id"]
            ):
                continue


            score = calculate_match(
                lost_data,
                found_data
            )


            if score >= 50:

                matches += 1


                text_score = text_match(
                    lost_data,
                    found_data
                )

                image_score = image_match(
                    lost_data["photo"],
                    found_data["photo"]
                )


                st.success(
                    "🔔 Possible Match Found!"
                )


                c1, c2 = st.columns(2)


                with c1:

                    st.subheader(
                        "🔴 Lost Item"
                    )

                    st.write(
                        "📌",
                        lost_data["item_name"]
                    )

                    st.write(
                        "📍",
                        lost_data["location"]
                    )

                    st.write(
                        "🎨",
                        lost_data["color"]
                    )

                    st.write(
                        "📝",
                        lost_data["description"]
                    )


                    if (
                        lost_data["photo"]
                        and os.path.exists(
                            lost_data["photo"]
                        )
                    ):

                        st.image(
                            lost_data["photo"],
                            width=250
                        )


                with c2:

                    st.subheader(
                        "🟢 Found Item"
                    )

                    st.write(
                        "📌",
                        found_data["item_name"]
                    )

                    st.write(
                        "📍",
                        found_data["location"]
                    )

                    st.write(
                        "🎨",
                        found_data["color"]
                    )

                    st.write(
                        "📝",
                        found_data["description"]
                    )


                    if (
                        found_data["photo"]
                        and os.path.exists(
                            found_data["photo"]
                        )
                    ):

                        st.image(
                            found_data["photo"],
                            width=250
                        )


                st.write(
                    "📝 Text Match:",
                    str(text_score) + "%"
                )

                st.write(
                    "📸 Image Match:",
                    str(image_score) + "%"
                )

                st.write(
                    "🎯 Final AI Score:",
                    str(score) + "%"
                )

                st.progress(
                    min(score / 100, 1.0)
                )


                # =================================
                # CLAIM REQUEST
                # =================================

                st.subheader(
                    "🤝 Contact Owner"
                )

                claim_message = st.text_area(
                    "Write a message",
                    placeholder=(
                        "I think this is my item. "
                        "Please verify."
                    ),
                    key=(
                        "message_"
                        + str(lost_data["id"])
                        + "_"
                        + str(found_data["id"])
                    )
                )


                if st.button(
                    "📩 Send Claim Request",
                    key=(
                        "claim_"
                        + str(lost_data["id"])
                        + "_"
                        + str(found_data["id"])
                    )
                ):

                    if not claim_message.strip():

                        st.warning(
                            "⚠️ Please write a message."
                        )

                    else:

                        # If lost user is claiming found item,
                        # receiver = found item's owner.
                        create_claim_request(
                            found_data["id"],
                            st.session_state.user_id,
                            found_data["user_id"],
                            claim_message
                        )


                        add_notification(
                            found_data["user_id"],
                            lost_data["id"],
                            found_data["id"],
                            (
                                "🤝 New claim request for "
                                + str(found_data["item_name"])
                            ),
                            score
                        )


                        st.success(
                            "✅ Claim request sent successfully!"
                        )


                st.divider()


    if matches == 0:

        st.warning(
            "🔍 No strong match found."
        )


# =========================================
# MY REPORTS
# =========================================

elif menu == "📂 My Reports":

    st.header("📂 My Reports")


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            id,
            item_type,
            item_name,
            description,
            color,
            location,
            photo,
            uploaded_at,
            status
        FROM items
        WHERE user_id=%s
        ORDER BY id DESC
    """, (
        st.session_state.user_id,
    ))

    items = cursor.fetchall()

    conn.close()


    if not items:

        st.info(
            "📭 No reports yet."
        )

    else:

        for item in items:

            icon = (
                "🔴"
                if item[1] == "Lost"
                else "🟢"
            )


            with st.expander(
                icon
                + " "
                + str(item[2])
                + " — "
                + str(item[1])
            ):

                st.write(
                    "📌 Type:",
                    item[1]
                )

                st.write(
                    "🎨 Color:",
                    item[4]
                )

                st.write(
                    "📍 Location:",
                    item[5]
                )

                st.write(
                    "📝 Description:",
                    item[3]
                )

                st.write(
                    "🕒 Uploaded:",
                    item[7] or "Old Record"
                )

                st.write(
                    "📊 Status:",
                    item[8] or "Active"
                )


                if (
                    item[6]
                    and os.path.exists(item[6])
                ):

                    st.image(
                        item[6],
                        width=280
                    )


# =========================================
# NOTIFICATIONS
# =========================================

elif menu.startswith("🔔 Notifications"):

    st.header("🔔 Notifications")


    notifications = get_notifications(
        st.session_state.user_id
    )


    if not notifications:

        st.success(
            "🎉 No notifications yet."
        )

    else:

        unread = get_unread_count(
            st.session_state.user_id
        )


        if unread > 0:

            st.warning(
                "🔔 You have "
                + str(unread)
                + " unread notification(s)."
            )


            if st.button(
                "✅ Mark All as Read"
            ):

                mark_all_read(
                    st.session_state.user_id
                )

                st.rerun()


        for notification in notifications:

            if notification[4] == 0:

                st.warning(
                    "🔔 NEW NOTIFICATION"
                )

            else:

                st.info(
                    "📢 Notification"
                )


            st.write(
                notification[1]
            )

            st.write(
                "🎯 AI Score:",
                str(notification[2]) + "%"
            )

            st.caption(
                "🕒 "
                + str(notification[3])
            )

            st.divider()


# =========================================
# CLAIM REQUESTS
# =========================================

elif menu == "🤝 Claim Requests":

    st.header("🤝 Claim Requests")


    received = get_received_claims(
        st.session_state.user_id
    )

    sent = get_sent_claims(
        st.session_state.user_id
    )


    received_tab, sent_tab = st.tabs(
        [
            "📥 Received",
            "📤 Sent"
        ]
    )


    # =====================================
    # RECEIVED
    # =====================================

    with received_tab:

        if not received:

            st.info(
                "📭 No received requests."
            )

        else:

            for request in received:

                claim_id = request[0]
                item_id = request[1]
                sender_id = request[2]
                message = request[3]
                status = request[4]
                created_at = request[5]
                item_name = request[6]
                item_type = request[7]
                sender_name = request[8]


                with st.expander(
                    "📦 "
                    + str(item_name)
                    + " — "
                    + str(status)
                ):

                    st.write(
                        "👤 From:",
                        sender_name
                    )

                    st.write(
                        "📌 Item:",
                        item_name
                    )

                    st.write(
                        "📝 Message:",
                        message
                    )

                    st.write(
                        "🕒 Time:",
                        created_at
                    )

                    st.write(
                        "📊 Status:",
                        status
                    )


                    if status == "Pending":

                        col1, col2 = st.columns(2)


                        with col1:

                            if st.button(
                                "✅ Accept",
                                key=(
                                    "accept_"
                                    + str(claim_id)
                                )
                            ):

                                update_claim_status(
                                    claim_id,
                                    "Accepted"
                                )


                                # Item resolved
                                update_item_status(
                                    item_id,
                                    "Resolved"
                                )


                                # Notify sender
                                add_notification(
                                    sender_id,
                                    0,
                                    0,
                                    (
                                        "✅ Your claim request for "
                                        + str(item_name)
                                        + " was accepted."
                                    ),
                                    100
                                )


                                st.success(
                                    "✅ Request accepted! "
                                    "💬 Both users can now chat in the Chat section."
                                )

                                st.rerun()


                        with col2:

                            if st.button(
                                "❌ Reject",
                                key=(
                                    "reject_"
                                    + str(claim_id)
                                )
                            ):

                                update_claim_status(
                                    claim_id,
                                    "Rejected"
                                )


                                add_notification(
                                    sender_id,
                                    0,
                                    0,
                                    (
                                        "❌ Your claim request for "
                                        + str(item_name)
                                        + " was rejected."
                                    ),
                                    0
                                )


                                st.warning(
                                    "❌ Request rejected."
                                )

                                st.rerun()


    # =====================================
    # SENT
    # =====================================

    with sent_tab:

        if not sent:

            st.info(
                "📭 You have not sent any requests."
            )

        else:

            for request in sent:

                claim_id = request[0]
                message = request[2]
                status = request[3]
                created_at = request[4]
                item_name = request[5]
                receiver_name = request[6]


                with st.expander(
                    "📦 "
                    + str(item_name)
                    + " — "
                    + str(status)
                ):

                    st.write(
                        "👤 To:",
                        receiver_name
                    )

                    st.write(
                        "📝 Message:",
                        message
                    )

                    st.write(
                        "🕒 Time:",
                        created_at
                    )

                    st.write(
                        "📊 Status:",
                        status
                    )



# =========================================
# CHAT
# =========================================

elif menu == "💬 Chat":

    st.header("💬 Chat")

    st.info(
        "🤖 After an AI match, both users can use this private chat "
        "once the claim request is accepted."
    )

    chats = get_accepted_chats(
        st.session_state.user_id
    )

    if not chats:

        st.warning(
            "📭 There are no active chats yet."
        )

        st.caption(
            "First, a possible match must be found in AI Matching. "
            "Then the chat will open after the claim request is accepted."
        )

    else:

        for chat in chats:

            claim_id = chat[0]
            item_id = chat[1]
            sender_id = chat[2]
            receiver_id = chat[3]
            original_message = chat[4]
            created_at = chat[5]
            item_name = chat[6]
            sender_name = chat[7]
            receiver_name = chat[8]

            if st.session_state.user_id == sender_id:
                other_user_id = receiver_id
                other_user_name = receiver_name
            else:
                other_user_id = sender_id
                other_user_name = sender_name

            with st.expander(
                "💬 " + str(item_name) +
                " — Chat with " + str(other_user_name),
                expanded=True
            ):

                st.caption(
                    "🤝 Claim Request Accepted • " +
                    str(created_at)
                )

                messages = get_chat_messages(
                    claim_id,
                    st.session_state.user_id
                )

                if messages:

                    for msg in messages:

                        msg_sender_id = msg[1]
                        msg_sender_name = msg[2]
                        msg_text = msg[3]
                        msg_time = msg[4]

                        if (
                            msg_sender_id
                            == st.session_state.user_id
                        ):
                            st.success(
                                "You: " + str(msg_text)
                            )
                        else:
                            st.info(
                                str(msg_sender_name)
                                + ": "
                                + str(msg_text)
                            )

                        st.caption(
                            "🕒 " + str(msg_time)
                        )

                else:

                    st.write(
                        "💬 No messages yet."
                    )

                chat_input = st.text_input(
                    "Write a message",
                    placeholder=(
                        "Type your message here..."
                    ),
                    key="chat_input_" + str(claim_id)
                )

                if st.button(
                    "📩 Send",
                    key="send_chat_" + str(claim_id),
                    use_container_width=True
                ):

                    if not chat_input.strip():

                        st.warning(
                            "⚠️ Please write a message."
                        )

                    else:

                        send_chat_message(
                            claim_id,
                            st.session_state.user_id,
                            other_user_id,
                            chat_input
                        )

                        st.rerun()

                st.divider()

# =========================================
# DASHBOARD
# =========================================

elif menu == "📊 Dashboard":

    st.header("📊 Dashboard")


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT COUNT(*)
        FROM users
    """)

    users = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
    """)

    reports = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE item_type='Lost'
    """)

    lost = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE item_type='Found'
    """)

    found = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE status='Resolved'
    """)

    resolved = cursor.fetchone()[0]


    conn.close()


    c1, c2, c3, c4, c5 = st.columns(5)


    c1.metric(
        "👥 Users",
        users
    )

    c2.metric(
        "📦 Reports",
        reports
    )

    c3.metric(
        "🔴 Lost",
        lost
    )

    c4.metric(
        "🟢 Found",
        found
    )

    c5.metric(
        "✅ Resolved",
        resolved
    )


# =========================================
# ADMIN PANEL
# =========================================

elif menu == "👨‍💼 Admin Panel":

    if not st.session_state.is_admin:

        st.error(
            "🚫 Admin access required."
        )

        st.stop()


    st.header("👨‍💼 Admin Panel")

    st.success(
        "👑 Admin access granted."
    )


    conn = get_connection()

    cursor = conn.cursor()


    # =====================================
    # ADMIN STATS
    # =====================================

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COUNT(*) FROM items"
    )

    total_reports = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE item_type='Lost'
    """)

    total_lost = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE item_type='Found'
    """)

    total_found = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE status='Resolved'
    """)

    total_resolved = cursor.fetchone()[0]


    a, b, c, d, e = st.columns(5)


    a.metric(
        "👥 Users",
        total_users
    )

    b.metric(
        "📦 Reports",
        total_reports
    )

    c.metric(
        "🔴 Lost",
        total_lost
    )

    d.metric(
        "🟢 Found",
        total_found
    )

    e.metric(
        "✅ Resolved",
        total_resolved
    )


    st.divider()


    # =====================================
    # USERS
    # =====================================

    st.subheader(
        "👥 Registered Users"
    )


    cursor.execute("""
        SELECT
            id,
            name,
            username,
            is_admin
        FROM users
        ORDER BY id DESC
    """)

    users_data = cursor.fetchall()


    for user in users_data:

        role = (
            "👑 Admin"
            if user[3]
            else "👤 User"
        )

        st.write(
            "ID:",
            user[0],
            "|",
            user[1],
            "|",
            user[2],
            "|",
            role
        )


    st.divider()


    # =====================================
    # REPORTS
    # =====================================

    st.subheader(
        "📦 Manage Reports"
    )


    cursor.execute("""
        SELECT
            id,
            item_type,
            item_name,
            description,
            color,
            location,
            photo,
            uploaded_at,
            status,
            user_id
        FROM items
        ORDER BY id DESC
    """)

    reports_data = cursor.fetchall()

    conn.close()


    if not reports_data:

        st.info(
            "📭 No reports available."
        )


    for report in reports_data:

        report_id = report[0]
        item_type = report[1]
        item_name = report[2]
        description = report[3]
        color = report[4]
        location = report[5]
        photo = report[6]
        uploaded_at = report[7]
        status = report[8] or "Active"
        user_id = report[9]


        icon = (
            "🔴"
            if item_type == "Lost"
            else "🟢"
        )


        with st.expander(
            icon
            + " "
            + str(item_name)
            + " | ID: "
            + str(report_id)
        ):

            st.write(
                "📌 Type:",
                item_type
            )

            st.write(
                "📝 Description:",
                description
            )

            st.write(
                "🎨 Color:",
                color
            )

            st.write(
                "📍 Location:",
                location
            )

            st.write(
                "👤 User ID:",
                user_id
            )

            st.write(
                "🕒 Uploaded:",
                uploaded_at
            )

            st.write(
                "📊 Status:",
                status
            )


            if (
                photo
                and os.path.exists(photo)
            ):

                st.image(
                    photo,
                    width=250
                )


            col1, col2 = st.columns(2)


            with col1:

                if status != "Resolved":

                    if st.button(
                        "✅ Mark Resolved",
                        key=(
                            "resolve_"
                            + str(report_id)
                        )
                    ):

                        update_item_status(
                            report_id,
                            "Resolved"
                        )

                        st.success(
                            "✅ Item marked as resolved."
                        )

                        st.rerun()


            with col2:

                if st.button(
                    "🗑️ Delete Report",
                    key=(
                        "delete_"
                        + str(report_id)
                    )
                ):

                    deleted_photo = delete_item(
                        report_id
                    )


                    if (
                        deleted_photo
                        and os.path.exists(
                            deleted_photo
                        )
                    ):

                        try:
                            os.remove(
                                deleted_photo
                            )
                        except:
                            pass


                    st.success(
                        "🗑️ Report deleted."
                    )

                    st.rerun()