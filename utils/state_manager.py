user_state = {}

def save_order(user_id, items):
    user_state[user_id] = items

def get_order(user_id):
    return user_state.get(user_id)