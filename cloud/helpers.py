def username(login_info):
    if login_info:
        user = login_info.get("user")
        if user:
            data = user.get("data")
            if data:
                return data.get("username")
    
    return None
