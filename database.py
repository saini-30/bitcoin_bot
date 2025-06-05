from pymongo import MongoClient
import random
import string

# MongoDB connection
MONGO_URI = "mongodb+srv://harpreet:saini@cluster0.uszo25j.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client['teligram']
users_collection = db['users']

def generate_referral_code():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(12))

def distribute_referral_rewards(referred_by_code, new_user_bitcoin=2):
    """
    Distribute rewards through the referral chain.
    Each referrer gets half of what their direct referral gets.
    """
    if not referred_by_code:
        return
    
    # Find the direct referrer
    referrer = get_user_by_referral(referred_by_code)
    if not referrer:
        return
    
    # Calculate reward for direct referrer (half of new user's bitcoin)
    reward = new_user_bitcoin / 2
    
    # Update direct referrer's balance
    users_collection.update_one(
        {"referral_number": referred_by_code},
        {"$inc": {"bitcoin_balance": reward}}
    )
    
    # Continue up the referral chain
    if referrer.get('referred_by'):
        # The referrer's referrer gets half of what the referrer got
        distribute_referral_rewards(referrer['referred_by'], reward)

def register_user(email, password, referred_by=None):
    # Check if email is already used
    if users_collection.find_one({"email": email}):
        return None, "User already exists with this email"

    # If referral code is provided, make sure it exists
    if referred_by and not get_user_by_referral(referred_by):
        return None, "Invalid referral code"

    referral_number = generate_referral_code()
    
    # Every new user starts with 2 botcoin
    initial_bitcoin = 2
    
    user_data = {
        "email": email,
        "password": password,
        "referral_number": referral_number,
        "referred_by": referred_by if referred_by else None,
        "bitcoin_balance": initial_bitcoin
    }
    
    try:
        users_collection.insert_one(user_data)
        
        # Distribute rewards to referral chain if user was referred
        if referred_by:
            distribute_referral_rewards(referred_by, initial_bitcoin)
        
        return referral_number, None
    except Exception as e:
        return None, str(e)

def get_user_by_referral(referral_code):
    return users_collection.find_one({"referral_number": referral_code})

def get_user_by_email(email):
    return users_collection.find_one({"email": email})

def login_user(email, password):
    return users_collection.find_one({
        "email": email,
        "password": password
    })

def get_user_bitcoin_balance(email):
    user = users_collection.find_one({"email": email})
    return user.get('bitcoin_balance', 0) if user else 0

def update_user_bitcoin_balance(email, new_balance):
    """Update user's bitcoin balance"""
    users_collection.update_one(
        {"email": email},
        {"$set": {"bitcoin_balance": new_balance}}
    )

def add_bitcoin_to_user(email, amount):
    """Add bitcoin to user's balance"""
    users_collection.update_one(
        {"email": email},
        {"$inc": {"bitcoin_balance": amount}}
    )

def get_referral_chain(user_email):
    """Get the complete referral chain for a user (for debugging/admin purposes)"""
    user = get_user_by_email(user_email)
    if not user:
        return []
    
    chain = []
    current_referrer = user.get('referred_by')
    
    while current_referrer:
        referrer = get_user_by_referral(current_referrer)
        if not referrer:
            break
        chain.append({
            'email': referrer['email'],
            'referral_code': referrer['referral_number'],
            'bitcoin_balance': referrer.get('bitcoin_balance', 0)
        })
        current_referrer = referrer.get('referred_by')
    
    return chain

def get_user_referrals(referral_code):
    """Get all users who were referred by a specific referral code"""
    return list(users_collection.find({"referred_by": referral_code}))

# Migration function to add bitcoin_balance to existing users
def migrate_existing_users():
    """Add bitcoin_balance field to existing users who don't have it"""
    result = users_collection.update_many(
        {"bitcoin_balance": {"$exists": False}},
        {"$set": {"bitcoin_balance": 2}}
    )
    return result.modified_count