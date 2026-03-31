# app.py
# This is your Streamlit web interface for Finny.
# Run it with: streamlit run app.py

import streamlit as st
from parser import parse_bank_message
from agent import (
    ask_about_transaction,
    process_user_category_reply,
    get_spending_summary_response
)
from storage import load_all_transactions, get_summary_by_category
from datetime import datetime

# ── PAGE SETUP ────────────────────────────────────────────────────────────
# This configures the browser tab — title and icon
st.set_page_config(
    page_title="Finny — Finance Tracker",
    page_icon="💰",
    layout="wide"  # Use full width of the browser
)

# ── CUSTOM STYLING ────────────────────────────────────────────────────────
st.markdown("""
    <style>
    .big-title { font-size: 2.5rem; font-weight: 800; color: #2E86AB; }
    .subtitle  { font-size: 1rem; color: #888; margin-bottom: 2rem; }
    .stat-box  { 
        background: #f0f7ff; 
        border-radius: 12px; 
        padding: 1rem; 
        text-align: center;
        margin: 0.5rem 0;
    }
    .stat-number { font-size: 1.8rem; font-weight: 700; color: #2E86AB; }
    .stat-label  { font-size: 0.85rem; color: #666; }
    </style>
""", unsafe_allow_html=True)

# ── SESSION STATE SETUP ───────────────────────────────────────────────────
# What is session state?
# Streamlit reruns your entire script every time the user does anything.
# Session state is like a notepad that remembers things between reruns.
# Without it, every button click would wipe everything.

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []  # List of chat bubbles to display

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []  # Gemini's memory

if 'waiting_for_category' not in st.session_state:
    st.session_state.waiting_for_category = False  # Are we mid-conversation?

if 'current_amount' not in st.session_state:
    st.session_state.current_amount = None

if 'current_direction' not in st.session_state:
    st.session_state.current_direction = None


# ── HELPER: Add a message to chat ─────────────────────────────────────────
def add_message(role, text):
    """
    Add a message to the chat display.
    role = 'user' (you) or 'finny' (the AI)
    """
    st.session_state.chat_messages.append({
        'role': role,
        'text': text,
        'time': datetime.now().strftime('%I:%M %p')
    })


# ── LAYOUT: Two columns ───────────────────────────────────────────────────
# col1 = chat window (left, wider)
# col2 = summary panel (right, narrower)
col1, col2 = st.columns([2, 1])


# ════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Chat Interface
# ════════════════════════════════════════════════════════════════════════════
with col1:
    st.markdown('<div class="big-title">💰 Finny</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your friendly AI finance tracker</div>', unsafe_allow_html=True)

    # ── Show chat history ─────────────────────────────────────────────────
    # Loop through every message and display it as a chat bubble
    for msg in st.session_state.chat_messages:
        if msg['role'] == 'user':
            with st.chat_message('user'):
                st.write(msg['text'])
        else:
            with st.chat_message('assistant', avatar='💰'):
                st.write(msg['text'])

    # ── Show welcome message if chat is empty ─────────────────────────────
    if not st.session_state.chat_messages:
        with st.chat_message('assistant', avatar='💰'):
            st.write(
                "Hey! 👋 I'm Finny, your personal finance buddy!\n\n"
                "Paste a bank SMS message below and I'll help you track it. "
                "Or type something like **₹500 debited** to get started! 😊"
            )

    # ── Input box at the bottom ───────────────────────────────────────────
    # st.chat_input creates the message box at the bottom of the screen
    # The text inside is the placeholder (grey hint text)
    if st.session_state.waiting_for_category:
        placeholder = "What did you spend this money on? (e.g. food, travel, bills...)"
    else:
        placeholder = "Paste bank SMS or type e.g. ₹500 debited..."

    user_input = st.chat_input(placeholder)

    # ── Handle user input ─────────────────────────────────────────────────
    if user_input:

        # Show the user's message in chat
        add_message('user', user_input)

        # CASE 1: We're waiting for the user to tell us the category
        if st.session_state.waiting_for_category:
            with st.spinner('Finny is thinking... 💭'):
                category, confirmation = process_user_category_reply(
                    st.session_state.current_amount,
                    st.session_state.current_direction,
                    user_input,
                    st.session_state.conversation_history
                )

            add_message('finny', confirmation)

            if category:
                # Transaction saved successfully — reset state
                st.session_state.waiting_for_category = False
                st.session_state.current_amount = None
                st.session_state.current_direction = None
                st.session_state.conversation_history = []
            # If category is None, Finny asked a follow-up — keep waiting

        # CASE 2: New bank message coming in
        else:
            parsed = parse_bank_message(user_input)

            if parsed['parse_success']:
                # Successfully parsed — ask what they spent on
                st.session_state.current_amount = parsed['amount']
                st.session_state.current_direction = parsed['direction']

                with st.spinner('Finny is thinking... 💭'):
                    question = ask_about_transaction(
                        parsed['amount'],
                        parsed['direction'],
                        st.session_state.conversation_history
                    )

                add_message('finny', question)

                # Update conversation history for Gemini's memory
                st.session_state.conversation_history.append(
                    {'role': 'user', 'parts': [user_input]}
                )
                st.session_state.conversation_history.append(
                    {'role': 'model', 'parts': [question]}
                )

                # Now wait for user to tell us the category
                st.session_state.waiting_for_category = True

            else:
                # Couldn't parse — ask user to clarify
                add_message('finny',
                    "Hmm, I couldn't read that as a bank message 🤔\n\n"
                    "Try something like:\n"
                    "- **₹500 debited from your account**\n"
                    "- **Rs.1000 credited to your SBI account**"
                )

        # Rerun to refresh the chat display
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Summary Panel
# ════════════════════════════════════════════════════════════════════════════
with col2:
    st.markdown("### 📊 Your Summary")

    # ── This month's stats ────────────────────────────────────────────────
    current_month = datetime.now().strftime('%Y-%m')
    monthly_summary = get_summary_by_category(month=current_month)
    all_transactions = load_all_transactions()

    # Total spent this month
    total_spent = sum(
        t['amount'] for t in all_transactions
        if t['direction'] == 'debit' and t['month'] == current_month
    )

    # Total received this month
    total_received = sum(
        t['amount'] for t in all_transactions
        if t['direction'] == 'credit' and t['month'] == current_month
    )

    # Transaction count
    txn_count = len([
        t for t in all_transactions
        if t['month'] == current_month
    ])

    # Display stat boxes
    st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">₹{total_spent:,.0f}</div>
            <div class="stat-label">Spent this month</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">₹{total_received:,.0f}</div>
            <div class="stat-label">Received this month</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{txn_count}</div>
            <div class="stat-label">Transactions logged</div>
        </div>
    """, unsafe_allow_html=True)

    # ── Category breakdown ────────────────────────────────────────────────
    if monthly_summary:
        st.markdown("#### Where your money went:")
        for cat, amount in sorted(monthly_summary.items(), key=lambda x: -x[1]):
            # Progress bar showing proportion of total spending
            proportion = amount / total_spent if total_spent > 0 else 0
            st.markdown(f"**{cat.capitalize()}** — ₹{amount:,.0f}")
            st.progress(proportion)
    else:
        st.info("No transactions yet this month!")

    # ── Recent transactions ───────────────────────────────────────────────
    st.markdown("#### 🕐 Recent")
    recent = list(reversed(all_transactions[-5:]))  # Last 5, newest first

    if recent:
        for t in recent:
            icon = "🔴" if t['direction'] == 'debit' else "🟢"
            st.markdown(
                f"{icon} **₹{t['amount']:,.0f}** — {t['category'].capitalize()}  \n"
                f"<small>{t['date']}</small>",
                unsafe_allow_html=True
            )
    else:
        st.info("No transactions yet!")

    # ── Clear chat button ─────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        st.session_state.conversation_history = []
        st.session_state.waiting_for_category = False
        st.session_state.current_amount = None
        st.session_state.current_direction = None
        st.rerun()