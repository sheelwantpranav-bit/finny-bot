# agent.py
import json
import os

from groq import Groq

from storage import get_summary_by_category, save_transaction

SYSTEM_PROMPT = """You are Finny, a friendly personal finance tracking assistant for Indian users.

Your personality:
- Warm, casual, and encouraging like a helpful friend
- Use simple language and occasional emojis
- Never be robotic or boring
- Never judge spending habits

Your job when a transaction arrives:
1. Acknowledge the transaction warmly
2. Ask the user ONE simple question: what was this money spent on?
3. When the user replies, confirm what category you're saving it under
4. If the category is unclear, ask one gentle follow-up question

Standard categories: Food, Travel, Shopping, Entertainment, Bills, Health, Education, Salary, Refund, Transfer, Other

Rules:
- Keep responses short, max 2-3 lines
- Accept Hindi or mixed language naturally
- Never ask more than 2 questions in a row"""


def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    return Groq(api_key=api_key)


def ask_finny(prompt):
    client = get_client()
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


def ask_gemini(prompt, conversation_history=None):
    return ask_finny(prompt)


def ask_about_transaction(amount, direction, conversation_history=None):
    if direction == 'debit':
        prompt = (
            f"A bank transaction just happened: Rs.{amount} was debited from the user's account. "
            f"Ask them what they spent it on in a friendly way. Keep it to 1-2 lines."
        )
    else:
        prompt = (
            f"A bank transaction just happened: Rs.{amount} was credited to the user's account. "
            f"Ask them what this incoming money was for in a friendly way. Keep it to 1-2 lines."
        )
    return ask_finny(prompt)


def extract_category_reply(amount, direction, user_reply):
    extraction_prompt = f"""The user was asked about a Rs.{amount} {direction} transaction.
They replied: "{user_reply}"

Respond ONLY with a valid JSON object, nothing else:
{{"category": "food", "confidence": "high", "save": true}}

Rules:
- Use one of these if it fits: Food, Travel, Shopping, Entertainment, Bills, Health, Education, Salary, Refund, Transfer
- Otherwise use the user's own word as the category
- If reply is too vague like "idk" or "?", set "save" to false
- Always return valid JSON with exactly these 3 keys"""

    raw_response = ask_finny(extraction_prompt)
    clean = raw_response.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(lines[1:-1])

    try:
        data = json.loads(clean)
        category = str(data.get('category', user_reply)).strip()
        should_save = bool(data.get('save', True))
    except (json.JSONDecodeError, TypeError, ValueError):
        category = user_reply.strip()
        should_save = True

    return {
        'category': category,
        'save': should_save,
    }


def generate_clarification_question(amount, user_reply):
    prompt = (
        f"The user said '{user_reply}' but it's unclear. "
        f"Ask one friendly follow-up to clarify what they spent Rs.{amount} on."
    )
    return ask_finny(prompt)


def generate_save_confirmation(amount, direction, category):
    prompt = (
        f"You just saved Rs.{amount} {direction} under '{category}'. "
        f"Give a short friendly confirmation, 1-2 lines, use an emoji."
    )
    return ask_finny(prompt)


def process_user_category_reply(amount, direction, user_reply, conversation_history):
    extracted = extract_category_reply(amount, direction, user_reply)
    category = extracted['category']

    if not extracted['save']:
        followup = generate_clarification_question(amount, user_reply)
        return None, followup

    save_transaction(amount, direction, category, notes=user_reply)
    confirmation = generate_save_confirmation(amount, direction, category)
    return category, confirmation


def get_spending_summary_response(month=None):
    summary = get_summary_by_category(month=month)
    if not summary:
        return "Hmm, no spending recorded yet! Start by entering a transaction 😊"

    summary_text = "\n".join(
        f"{category.capitalize()}: Rs.{total}"
        for category, total in summary.items()
    )
    total_spent = sum(summary.values())
    prompt = (
        f"Here is the user's spending summary:\n{summary_text}\n"
        f"Total: Rs.{total_spent}\n\n"
        f"Present this in a friendly, readable way. "
        f"Add one encouraging observation. Keep it under 6 lines."
    )
    return ask_finny(prompt)
