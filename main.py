# main.py
# This is the entry point — the file you run to start your finance agent.
# Think of it as the front door of your application.
# It reads input, coordinates between parser → agent → storage.

import os
from parser import parse_bank_message
from agent import ask_about_transaction, process_user_category_reply, get_spending_summary_response
from storage import load_all_transactions

# ANSI color codes — these make terminal output colorful and readable
# \033[92m = green, \033[94m = blue, \033[93m = yellow, \033[0m = reset to normal
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def print_banner():
    print(f"""
{CYAN}{BOLD}
╔══════════════════════════════════════════╗
║   💰  Finny — Your Finance Tracker  💰  ║
║      Friendly AI Money Assistant         ║
╚══════════════════════════════════════════╝
{RESET}""")


def handle_transaction_flow(bank_message):
    """
    Full conversation flow for one transaction:
    1. Parse the bank message
    2. Ask the user what they spent on
    3. Save the answer
    """
    # Step 1: Parse the bank SMS
    parsed = parse_bank_message(bank_message)

    if not parsed['parse_success']:
        print(f"{YELLOW}⚠️  Couldn't read that message clearly. Please enter manually.{RESET}")
        amount = float(input("  Enter amount (₹): "))
        direction = input("  Debit or Credit? ").lower().strip()
    else:
        amount = parsed['amount']
        direction = parsed['direction']
        print(f"\n{GREEN}📩 Transaction detected: ₹{amount} — {direction.upper()}{RESET}")

    # Step 2: Ask Claude to start the conversation
    conversation_history = []
    
    print(f"\n{BLUE}Finny:{RESET}", end=" ")
    question = ask_about_transaction(amount, direction, conversation_history)
    print(question)

    # Track conversation history so Claude has context
    conversation_history.append({
        "role": "user",
        "content": f"₹{amount} was {direction}ed from the account. Ask what it was for."
    })
    conversation_history.append({
        "role": "assistant",
        "content": question
    })

    # Step 3: Get user's reply
    max_attempts = 3  # Don't loop forever if user keeps saying "idk"
    attempt = 0
    
    while attempt < max_attempts:
        user_reply = input(f"\n{GREEN}You:{RESET} ").strip()
        
        if not user_reply:
            print(f"{YELLOW}Please type something 😊{RESET}")
            continue

        # Add user reply to history
        conversation_history.append({
            "role": "user",
            "content": user_reply
        })

        # Step 4: Process and save
        category, confirmation = process_user_category_reply(
            amount, direction, user_reply, conversation_history
        )

        print(f"\n{BLUE}Finny:{RESET} {confirmation}")

        if category:  # Successfully saved
            print(f"\n{GREEN}✅ Logged: ₹{amount} | {direction.upper()} | {category.capitalize()}{RESET}")
            break
        else:
            # Claude asked a follow-up question — loop again
            conversation_history.append({
                "role": "assistant",
                "content": confirmation
            })
            attempt += 1

    if attempt == max_attempts:
        # If user couldn't clarify, save as "Other"
        from storage import save_transaction
        save_transaction(amount, direction, 'other', notes='category unclear')
        print(f"{YELLOW}Saved as 'Other' category.{RESET}")


def show_summary():
    """Show the user's spending summary."""
    print(f"\n{CYAN}📊 Fetching your spending summary...{RESET}\n")
    
    use_month = input("Filter by this month only? (y/n): ").strip().lower()
    
    if use_month == 'y':
        from datetime import datetime
        month = datetime.now().strftime('%Y-%m')
    else:
        month = None

    summary = get_spending_summary_response(month=month)
    print(f"\n{BLUE}Finny:{RESET} {summary}")


def show_history():
    """Show raw transaction history."""
    transactions = load_all_transactions()
    
    if not transactions:
        print(f"{YELLOW}No transactions recorded yet!{RESET}")
        return

    print(f"\n{CYAN}{BOLD}📋 Transaction History ({len(transactions)} entries){RESET}")
    print("-" * 60)
    
    for t in transactions[-20:]:  # Show last 20
        icon = "🔴" if t['direction'] == 'debit' else "🟢"
        print(f"  {icon} #{t['id']:3} | ₹{t['amount']:>8.2f} | {t['category']:<15} | {t['date']}")
    
    if len(transactions) > 20:
        print(f"\n  ... and {len(transactions) - 20} more older entries")


def main():
    """Main loop — the app keeps running until you quit."""
    
    # Check for API key before starting
    if not os.environ.get('GROQ_API_KEY'):
        print(f"""
{YELLOW}⚠️  API Key Missing!

Before running, set your Groq API key:

  Windows (PowerShell):
    $env:GROQ_API_KEY = "your-key-here"

  Mac/Linux:
    export GROQ_API_KEY="your-key-here"

Get your key at: https://console.groq.com/keys
{RESET}""")
        return

    print_banner()
    
    while True:
        print(f"""
{BOLD}What would you like to do?{RESET}
  {CYAN}1{RESET} — Enter a bank message (simulate SMS)
  {CYAN}2{RESET} — View spending summary  
  {CYAN}3{RESET} — View transaction history
  {CYAN}q{RESET} — Quit
""")
        
        choice = input("Your choice: ").strip().lower()

        if choice == '1':
            print(f"\n{YELLOW}Paste your bank SMS message (or press Enter to use a test message):{RESET}")
            msg = input("> ").strip()
            
            if not msg:
                # Use a test message if user pressed Enter
                msg = "₹150 debited from your SBI account for UPI transaction"
                print(f"{YELLOW}Using test message: {msg}{RESET}")
            
            handle_transaction_flow(msg)

        elif choice == '2':
            show_summary()

        elif choice == '3':
            show_history()

        elif choice == 'q':
            print(f"\n{CYAN}Goodbye! Keep tracking those rupees 💰{RESET}\n")
            break

        else:
            print(f"{YELLOW}Please enter 1, 2, 3, or q{RESET}")


# Run the app
if __name__ == "__main__":
    main()
