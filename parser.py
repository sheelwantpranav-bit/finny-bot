# parser.py
import re

def parse_bank_message(message):
    message_lower = message.lower()

    amount = None
    match = re.search(r'(?:rs\.?|inr|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)', message_lower)
    if not match:
        match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rs|rupees|inr)', message_lower)
    if match:
        amount = float(match.group(1).replace(',', ''))

    direction = None
    debit_keywords = ['debited', 'deducted', 'spent', 'withdrawn', 'paid', 'debit']
    credit_keywords = ['credited', 'received', 'added', 'deposited', 'credit', 'refund']

    for word in debit_keywords:
        if word in message_lower:
            direction = 'debit'
            break

    if direction is None:
        for word in credit_keywords:
            if word in message_lower:
                direction = 'credit'
                break

    return {
        'amount': amount,
        'direction': direction,
        'raw_message': message,
        'parse_success': amount is not None and direction is not None
    }