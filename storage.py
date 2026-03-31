# storage.py
# This file saves transactions and pending conversations to JSON files.

import json
import os
from datetime import datetime
from uuid import uuid4

DATA_FILE = os.path.join('data', 'transactions.json')
PENDING_FILE = os.path.join('data', 'pending_transactions.json')


def ensure_json_file_exists(path, default_value):
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default_value, f, indent=2)


def ensure_data_file_exists():
    ensure_json_file_exists(DATA_FILE, [])


def ensure_pending_file_exists():
    ensure_json_file_exists(PENDING_FILE, [])


def load_all_transactions():
    ensure_data_file_exists()
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def save_all_transactions(transactions):
    ensure_data_file_exists()
    with open(DATA_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)


def save_transaction(
    amount,
    direction,
    category,
    notes='',
    source='manual',
    raw_message='',
    sms_sender='',
    source_key='',
):
    transactions = load_all_transactions()
    new_entry = {
        'id': len(transactions) + 1,
        'amount': amount,
        'direction': direction,
        'category': category.lower().strip(),
        'notes': notes,
        'source': source,
        'raw_message': raw_message,
        'sms_sender': sms_sender,
        'source_key': source_key,
        'timestamp': datetime.now().isoformat(),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'month': datetime.now().strftime('%Y-%m'),
    }
    transactions.append(new_entry)
    save_all_transactions(transactions)
    return new_entry


def get_summary_by_category(month=None):
    transactions = load_all_transactions()
    filtered = [
        transaction for transaction in transactions
        if transaction['direction'] == 'debit'
        and (month is None or transaction['month'] == month)
    ]

    summary = {}
    for transaction in filtered:
        category = transaction['category']
        if category not in summary:
            summary[category] = 0
        summary[category] += transaction['amount']
    return summary


def load_pending_transactions():
    ensure_pending_file_exists()
    with open(PENDING_FILE, 'r') as f:
        return json.load(f)


def save_pending_transactions(pending_transactions):
    ensure_pending_file_exists()
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending_transactions, f, indent=2)


def create_pending_transaction(
    telegram_user_id,
    amount,
    direction,
    raw_message,
    sender='',
    received_at='',
    dedupe_key='',
):
    pending_transactions = load_pending_transactions()
    now = datetime.now().isoformat()
    entry = {
        'id': str(uuid4()),
        'telegram_user_id': int(telegram_user_id),
        'amount': amount,
        'direction': direction,
        'raw_message': raw_message,
        'sender': sender,
        'received_at': received_at,
        'dedupe_key': dedupe_key,
        'status': 'pending',
        'followup_count': 0,
        'created_at': now,
        'updated_at': now,
    }
    pending_transactions.append(entry)
    save_pending_transactions(pending_transactions)
    return entry


def get_pending_transactions_for_user(telegram_user_id):
    pending_transactions = load_pending_transactions()
    active_transactions = [
        transaction for transaction in pending_transactions
        if transaction.get('telegram_user_id') == int(telegram_user_id)
        and transaction.get('status') == 'pending'
    ]
    return sorted(active_transactions, key=lambda transaction: transaction.get('created_at', ''))


def get_oldest_pending_transaction(telegram_user_id):
    active_transactions = get_pending_transactions_for_user(telegram_user_id)
    return active_transactions[0] if active_transactions else None


def update_pending_transaction(pending_id, **updates):
    pending_transactions = load_pending_transactions()
    for transaction in pending_transactions:
        if transaction.get('id') == pending_id:
            transaction.update(updates)
            transaction['updated_at'] = datetime.now().isoformat()
            save_pending_transactions(pending_transactions)
            return transaction
    return None


def mark_pending_transaction_completed(pending_id, category='', notes=''):
    return update_pending_transaction(
        pending_id,
        status='completed',
        category=category,
        notes=notes,
        completed_at=datetime.now().isoformat(),
    )


def has_seen_source_key(source_key):
    if not source_key:
        return False

    for transaction in load_all_transactions():
        if transaction.get('source_key') == source_key:
            return True

    for pending_transaction in load_pending_transactions():
        if pending_transaction.get('dedupe_key') == source_key:
            return True

    return False
